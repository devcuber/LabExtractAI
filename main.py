import logging

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from providers.gemini_provider import GeminiLLMProvider
from providers.mock_llm_provider import MockLLMProvider
from services.lab_service import LabAnalyzerService
from utils.pdf_utils import PdfPasswordRequiredError, PdfIncorrectPasswordError
from dotenv import load_dotenv
import os
import asyncio

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

    try:
        result = await lab_service.extract_and_transform(content, password=password)
    except PdfPasswordRequiredError:
        raise HTTPException(status_code=422, detail="El PDF requiere contraseña.")
    except PdfIncorrectPasswordError:
        raise HTTPException(status_code=422, detail="La contraseña proporcionada es incorrecta.")

    return result