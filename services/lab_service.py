import json
import logging
from core.base_llm_provider import BaseLLMProvider
from transformers.fhir_tabular_transformer import FHIRTabularTransformer
from utils.csv_utils import list_to_csv_string
from utils.pdf_utils import PdfUtils

logger = logging.getLogger(__name__)

class LabAnalyzerService:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def extract_data(self, file_content: bytes) -> dict:
        prompt = """
        Act as an expert in HL7 FHIR R4. Analyze all laboratory tests 
        from the attached file and create a single FHIR Observation resource 
        that acts as a general panel. Use the component field to include all 
        quantitative and qualitative results found in the document. 
        Omit empty fields, do not use dataAbsentReason, and respond strictly 
        with pure JSON only, with no markdown code blocks or additional text.
        """
        
        response_text = self.llm.ask_with_file(prompt, file_content)
        
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)

    async def extract_and_transform(self, file_content: bytes, password: str | None = None) -> dict:
        """
        Orquesta el flujo completo: 
        1. Si el PDF está protegido con contraseña, lo desbloquea.
        2. Envía el PDF a extract_data para obtener el JSON del recurso FHIR.
        3. Genera filas verticales para cada parámetro/componente.
        4. Convierte la lista de filas a un string CSV vertical.
        5. Retorna ambos resultados listos para ser consumidos por el endpoint.
        """
        if PdfUtils.is_pdf(file_content):
            logger.info("El usuario subió un archivo reconocido como PDF.")            
            file_content = PdfUtils.unlock_pdf(file_content, password)
            
        json_data = await self.extract_data(file_content)        
        vertical_rows = FHIRTabularTransformer.observation_to_vertical_rows(json_data)        
        csv_data = list_to_csv_string(vertical_rows)
        
        return {
            "json_data": json_data,
            "csv_data": csv_data
        }