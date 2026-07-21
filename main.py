from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from providers.gemini_provider import GeminiLLMProvider
from services.lab_service import LabAnalyzerService
from dotenv import load_dotenv
import os
import asyncio

app = FastAPI()
load_dotenv()
llm_provider = GeminiLLMProvider(api_key=os.getenv("GOOGLE_API_KEY"))
lab_service = LabAnalyzerService(llm_provider=llm_provider)

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.post("/api/v1/extract")
async def extract(file: UploadFile = File(...)):
    content = await file.read()    
    result = await lab_service.extract_data(content)
    return result