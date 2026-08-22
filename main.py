import logging

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from google.genai import types
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

system_prompt = """
You are an expert in HL7 FHIR R4, specialized in clinical laboratory data structures.
Your sole purpose is to analyze medical laboratory reports and map them into a single 
valid FHIR Observation resource acting as a general panel.

STRICT RULES:
1. Use the 'component' field to include all quantitative and qualitative results found in the document.
2. Omit empty fields completely.
3. NEVER use dataAbsentReason.
"""

gemini_config = types.GenerateContentConfig(
    temperature=0.0,
    system_instruction=system_prompt,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    response_mime_type="application/json",
    thinking_config=types.ThinkingConfig(thinking_budget=0),
)

llm_provider = GeminiLLMProvider(api_key=os.getenv("GOOGLE_API_KEY"), config=gemini_config)
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
        # e.args[0] contendrá el mensaje exacto de Google
        raise HTTPException(status_code=503, detail=str(e))    
    return result