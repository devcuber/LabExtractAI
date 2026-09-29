import logging

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.genai import types
from providers.gemini_provider import GeminiLLMProvider
from providers.mock_llm_provider import MockLLMProvider
from services.lab_service import (
    LabAnalyzerService,
    LabExtractionError,
    LoincSelectionError,
    FhirConstructionError,
)
from services.loinc_service import LoincService, LoincServiceError
from models.lab_report import ExtractedLabReport
from models.loinc import SelectedLoinc
from utils.pdf_utils import PdfPasswordRequiredError, PdfIncorrectPasswordError
from utils.file_utils import UnsupportedFileTypeError
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI()
load_dotenv()

# ---------------------------------------------------------------------------
# Configuración de CORS
# ---------------------------------------------------------------------------
origins = [
    "http://localhost:3000",       # Para desarrollo local (React, Vite, etc.)
    "http://localhost:5500",       # Para Live Server
    "http://127.0.0.1:5500",
    "https://cdie.io",
    "https://cdiefrontend.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Si prefieres restringirlo por seguridad, cambia ["*"] por la lista 'origins' de arriba
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# System instruction — IA #1: extracción documental
#
# Responsabilidad única: interpretar el documento y devolver un
# ExtractedLabReport. NO busca ni inventa códigos LOINC, NO construye FHIR.
# ---------------------------------------------------------------------------
extraction_system_prompt = """
You are an expert at reading medical laboratory reports (PDF or image).
Your sole purpose is to analyze the attached document and extract its
information into the requested structured format (ExtractedLabReport).

Extract, when present in the document:
- General report data: patient name, patient identifier (and its type,
  e.g. "expediente", "folio", "número de orden", when it can be determined),
  and the report/document date.
- Every individual test result: name, numeric value, textual value (when
  the result is not numeric), unit, reference range, and interpretation
  (only when it appears explicitly in the document).

Rules:
- Extract the information exactly as it appears in the document.
- Preserve the context available for each result.
- Distinguish clearly between general report data and individual results.
- If a field cannot be determined with reasonable certainty, leave it as
  null. Never invent identifiers, dates, values, or patient information.

You must NOT:
- search for LOINC codes;
- invent LOINC codes;
- select LOINC candidates;
- build a Coding, CodeableConcept, or any FHIR structure;
- build the final FHIR Observation.
Your only responsibility is extracting what the document says.
"""

extraction_config = types.GenerateContentConfig(
    temperature=0.0,
    system_instruction=extraction_system_prompt,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    response_mime_type="application/json",
    response_schema=ExtractedLabReport,
    thinking_config=types.ThinkingConfig(thinking_budget=0),
)

# ---------------------------------------------------------------------------
# System instruction — IA #2: selección del mejor candidato LOINC
#
# Responsabilidad única: elegir, entre los candidatos reales obtenidos desde
# la LOINC Search API, el que mejor representa semánticamente un resultado.
# ---------------------------------------------------------------------------
loinc_selection_system_prompt = """
You are an expert in clinical laboratory terminology and LOINC coding.
You will receive one laboratory result and a list of real LOINC candidates
obtained from the official LOINC Search API for that result.

Your sole task is to select the candidate that best semantically represents
the given result, using all the context available (name, value, unit,
reference range, interpretation).

You must NOT:
- invent LOINC codes;
- use a code that is not among the provided candidates;
- modify the code or display of any candidate;
- re-extract or reinterpret the original document.

Return exactly one candidate from the provided list, using its exact code
and display as given.
"""

loinc_selection_config = types.GenerateContentConfig(
    temperature=0.0,
    system_instruction=loinc_selection_system_prompt,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    response_mime_type="application/json",
    response_schema=SelectedLoinc,
    thinking_config=types.ThinkingConfig(thinking_budget=0),
)

api_key = os.getenv("GOOGLE_API_KEY")

extraction_llm = GeminiLLMProvider(api_key=api_key, config=extraction_config)
loinc_selection_llm = GeminiLLMProvider(api_key=api_key, config=loinc_selection_config)
# extraction_llm = MockLLMProvider()          # ACTIVAR PARA PRUEBAS LOCALES SIN CONSUMIR LA API DE GOOGLE
# loinc_selection_llm = MockLLMProvider()     # ACTIVAR PARA PRUEBAS LOCALES SIN CONSUMIR LA API DE GOOGLE

loinc_service = LoincService(
    username=os.getenv("LOINC_USERNAME"),
    password=os.getenv("LOINC_PASSWORD"),
    base_url=os.getenv("LOINC_BASE_URL", LoincService.DEFAULT_BASE_URL),
)

lab_service = LabAnalyzerService(
    extraction_llm=extraction_llm,
    loinc_selection_llm=loinc_selection_llm,
    loinc_service=loinc_service,
)


@app.post("/api/v1/analyze-lab")
async def analyze_lab(
    file: UploadFile = File(...),
    password: str | None = Form(None)
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
    except LabExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LoincServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LoincSelectionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FhirConstructionError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return result