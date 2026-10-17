import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from urllib.parse import quote
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from google.genai import types
from psycopg_pool import AsyncConnectionPool

from models.fhir_observation import FhirObservation
from models.lab_extraction_request import LabExtractionRequestListItem
from providers.gemini_provider import GeminiLLMProvider
from providers.mock_llm_provider import MockLLMProvider
from repositories.lab_extraction_request_repository import LabExtractionRequestRepository
from services.lab_service import (
    ExtractionRequestFailedError,
    ExtractionRequestNotFoundError,
    ExtractionResultMissingError,
    ExtractionResultNotReadyError,
    LabAnalyzerService,
)
from workers.lab_extraction_worker import LabExtractionWorker
from utils.file_utils import UnsupportedFileTypeError
from utils.pdf_utils import PdfIncorrectPasswordError, PdfPasswordRequiredError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

load_dotenv()

system_prompt = """
You are an expert in HL7 FHIR R4, specialized in clinical laboratory data structures.
Your sole purpose is to analyze medical laboratory reports and map them into a single
valid FHIR Observation resource acting as a general panel.

Use the 'component' field to include every quantitative and qualitative result found
in the document. Do not skip results.

For every 'code' field (both the panel-level code and each component's code):
- ALWAYS attempt to map the result to its standard LOINC code. Common lab analytes
  (glucose, hemoglobin, hematocrit, urinalysis parameters, complete blood count,
  cholesterol, etc.) have well-known LOINC codes — actively recall and use them,
  do not default to skipping this step.

- 'coding.system' must be "http://loinc.org", 'coding.code' the LOINC number,
  'coding.display' the official LOINC name.
- 'text' must always contain the exact original wording used by the laboratory,
  verbatim, regardless of whether a LOINC match was found.

Only leave 'coding' empty for genuinely ambiguous or non-standard analytes where no
reasonable LOINC match exists — do not guess a code you are not confident about.

If a patient name appears in the document, set it as 'subject.display'.
Never populate 'subject.reference' — that field must remain empty, as it refers to a
persisted Patient resource that does not exist at extraction time.

If a report/folio number appears in the document, add it as an entry in 'identifier',
using 'identifier.value' for the number itself.
"""

gemini_config = types.GenerateContentConfig(
    temperature=0.0,
    system_instruction=system_prompt,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    response_mime_type="application/json",
    response_schema=FhirObservation,
    thinking_config=types.ThinkingConfig(thinking_budget=0),
)

llm_provider = GeminiLLMProvider(
    api_key=os.getenv("GOOGLE_API_KEY"),
    config=gemini_config,
)
# llm_provider = MockLLMProvider() # ACTIVAR PARA PRUEBAS LOCALES SIN CONSUMIR LA API DE GOOGLE


@asynccontextmanager
async def lifespan(application: FastAPI):
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL no está configurada.")

    pool = AsyncConnectionPool(conninfo=database_url, open=False)
    await pool.open()
    application.state.pool = pool
    repository = LabExtractionRequestRepository(pool)
    application.state.lab_service = LabAnalyzerService(
        llm_provider=llm_provider,
        extraction_request_repository=repository,
    )
    application.state.lab_extraction_queue = asyncio.Queue()
    application.state.lab_extraction_worker = LabExtractionWorker(
        queue=application.state.lab_extraction_queue,
        repository=repository,
        lab_service=application.state.lab_service,
    )
    await repository.reset_recent_processing_to_pending()
    for request_id in await repository.list_recent_pending_ids():
        application.state.lab_extraction_queue.put_nowait(request_id)
    application.state.lab_extraction_worker_task = asyncio.create_task(
        application.state.lab_extraction_worker.run(),
        name="lab-extraction-worker",
    )
    try:
        yield
    finally:
        application.state.lab_extraction_worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await application.state.lab_extraction_worker_task
        await pool.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_lab_service(request: Request) -> LabAnalyzerService:
    return request.app.state.lab_service


@app.get("/")
async def read_index():
    return FileResponse("index.html")


@app.post("/api/v1/analyze-lab")
async def analyze_lab(
    file: UploadFile = File(...),
    password: str | None = Form(None),
    lab_service: LabAnalyzerService = Depends(get_lab_service),
):
    content = await file.read()

    try:
        result = await lab_service.extract_and_transform(content, password=password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PdfPasswordRequiredError:
        raise HTTPException(status_code=422, detail="El PDF requiere contraseña.")
    except PdfIncorrectPasswordError:
        raise HTTPException(status_code=422, detail="La contraseña proporcionada es incorrecta.")
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return result


@app.post("/api/v1/lab-extraction-requests", status_code=status.HTTP_201_CREATED)
async def create_lab_extraction_request(
    http_request: Request,
    file: UploadFile = File(...),
    password: str | None = Form(None),
    lab_service: LabAnalyzerService = Depends(get_lab_service),
):
    content = await file.read()

    try:
        request = await lab_service.enqueue_for_extraction(
            file_content=content,
            original_filename=file.filename,
            password=password,
        )
        await http_request.app.state.lab_extraction_queue.put(request.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PdfPasswordRequiredError:
        raise HTTPException(status_code=422, detail="El PDF requiere contraseña.")
    except PdfIncorrectPasswordError:
        raise HTTPException(status_code=422, detail="La contraseña proporcionada es incorrecta.")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "id": str(request.id),
        "status": request.status.value,
        "created_at": request.created_at,
    }

@app.get("/api/v1/lab-extraction-requests/{request_id}/result")
async def get_lab_extraction_result(
    request_id: UUID,
    lab_service: LabAnalyzerService = Depends(get_lab_service),
):
    try:
        return await lab_service.get_extraction_result(request_id)
    except ExtractionRequestNotFoundError:
        raise HTTPException(status_code=404, detail="La solicitud de extracción no existe.")
    except ExtractionResultNotReadyError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "La extracción aún no está completada.",
                "status": error.status.value,
            },
        )
    except ExtractionRequestFailedError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "La extracción falló.",
                "error": error.error_message,
            },
        )
    except ExtractionResultMissingError:
        raise HTTPException(
            status_code=500,
            detail="La solicitud está completada, pero no contiene resultado.",
        )


@app.get("/api/v1/lab-extraction-requests/{request_id}/csv")
async def download_lab_extraction_csv(
    request_id: UUID,
    lab_service: LabAnalyzerService = Depends(get_lab_service),
):
    try:
        csv_data, original_filename = await lab_service.get_extraction_csv(request_id)
    except ExtractionRequestNotFoundError:
        raise HTTPException(status_code=404, detail="La solicitud de extracción no existe.")
    except ExtractionResultNotReadyError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "La extracción aún no está completada.",
                "status": error.status.value,
            },
        )
    except ExtractionRequestFailedError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "La extracción falló.",
                "error": error.error_message,
            },
        )
    except ExtractionResultMissingError:
        raise HTTPException(
            status_code=500,
            detail="La solicitud está completada, pero no contiene resultado.",
        )

    filename = f"{Path(original_filename).stem}_clinical_data.csv"
    encoded_filename = quote(filename)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
            ),
        },
    )


@app.get("/api/v1/lab-extraction-requests", response_model=list[LabExtractionRequestListItem])
async def list_lab_extraction_requests(
    lab_service: LabAnalyzerService = Depends(get_lab_service),
):
    return await lab_service.list_extraction_requests()
