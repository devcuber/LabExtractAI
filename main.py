from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from providers.gemini_provider import GeminiLLMProvider
from providers.mock_llm_provider import MockLLMProvider
from services.lab_service import LabAnalyzerService
from utils.pdf_utils import PdfPasswordRequiredError, PdfIncorrectPasswordError
from services.file_type_detector import FileTypeDetector
from dotenv import load_dotenv
import os

app = FastAPI()
load_dotenv()
llm_provider = GeminiLLMProvider(api_key=os.getenv("GOOGLE_API_KEY"))
#llm_provider = MockLLMProvider() #ACTIVAR PARA PRUEBAS LOCALES SIN CONSUMIR LA API DE GOOGLE
lab_service = LabAnalyzerService(llm_provider=llm_provider)
file_type_detector = FileTypeDetector()


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

    mime_type = file_type_detector.detect(content, file.filename, file.content_type)
    if not file_type_detector.is_allowed(mime_type):
        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Sube un PDF, PNG, JPG o WEBP.",
        )

    try:
        result = await lab_service.extract_and_transform(content, mime_type, password=password)
    except PdfPasswordRequiredError:
        raise HTTPException(status_code=422, detail="El PDF requiere contraseña.")
    except PdfIncorrectPasswordError:
        raise HTTPException(status_code=422, detail="La contraseña proporcionada es incorrecta.")

    return result