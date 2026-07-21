from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from providers.gemini_provider import GeminiLLMProvider
#from providers.mock_llm_provider import MockLLMProvider
from services.lab_service import LabAnalyzerService
from dotenv import load_dotenv
import os
import asyncio

app = FastAPI()
load_dotenv()
llm_provider = GeminiLLMProvider(api_key=os.getenv("GOOGLE_API_KEY"))
#llm_provider = MockLLMProvider()
lab_service = LabAnalyzerService(llm_provider=llm_provider)

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.post("/api/v1/analyze-lab")
async def analyze_lab(file: UploadFile = File(...)):
    content = await file.read()    
    result = await lab_service.extract_and_transform(content)
    return result