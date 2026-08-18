import logging

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from providers.gemini_provider import GeminiLLMProvider
from providers.mock_llm_provider import MockLLMProvider
from services.lab_service import LabAnalyzerService
from utils.pdf_utils import PdfPasswordRequiredError, PdfIncorrectPasswordError
from utils.file_utils import UnsupportedFileTypeError
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI()
load_dotenv()
llm_provider = GeminiLLMProvider(api_key=os.getenv("GOOGLE_API_KEY"))
#llm_provider = MockLLMProvider() #ACTIVAR PARA PRUEBAS LOCALES SIN CONSUMIR LA API DE GOOGLE
lab_service = LabAnalyzerService(llm_provider=llm_provider)


@app.get("/")
async def read_index():
    return FileResponse("index.html")


@app.post("/api/v1/analyze-lab")
async def analyze_lab(
    file: UploadFile = File(...),
    password: str | None = Form(None)
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    try:
        result = await lab_service.extract_and_transform(content, password=password)
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PdfPasswordRequiredError:
        raise HTTPException(status_code=422, detail="El PDF requiere contraseña.")
    except PdfIncorrectPasswordError:
        raise HTTPException(status_code=422, detail="La contraseña proporcionada es incorrecta.")
    except ServerError as e:
        if e.code == 503:
            raise HTTPException(status_code=503, detail="El modelo está experimentando alta demanda en este momento. Por favor, inténtalo de nuevo en unos minutos.")
        raise HTTPException(status_code=500, detail=str(e))
    return result