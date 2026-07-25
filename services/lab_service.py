import json
import io
import csv
from core.base_llm_provider import BaseLLMProvider
from transformers.fhir_tabular_transformer import FHIRTabularTransformer
from utils.csv_utils import dict_to_csv_string
from utils.pdf_utils import PdfUtils

class LabAnalyzerService:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def extract_data(self, file_content: bytes, mime_type: str = "application/pdf") -> dict:
        prompt = """
        Actúa como un experto en HL7 FHIR R4. Crea un recurso 'Observation' 
        basado en el archivo adjunto. Omite campos vacíos, no uses dataAbsentReason, 
        responde solo con el JSON puro.
        """

        # Pasamos el mime_type real (PDF o imagen) al provider
        response_text = self.llm.ask_with_file(prompt, file_content, mime_type)
        
        # Limpieza
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)


    async def extract_and_transform(self, file_content: bytes, password: str | None = None) -> dict:
        """
        Orquesta el flujo completo: 
        1. Si el PDF está protegido con contraseña, lo desbloquea
        2. Envía el archivo (PDF o imagen) a extract_data para obtener el JSON del recurso FHIR.
        3. Pasa el JSON al aplanador para generar el CSV tabular dinámico.
        4. Retorna ambos resultados listos para ser consumidos por el endpoint.
        """
        if PdfUtils.is_pdf(file_content):
            file_content = PdfUtils.unlock_pdf(file_content, password)
        json_data = await self.extract_data(file_content)        
        flat_data = FHIRTabularTransformer.flatten_fhir_to_dict(json_data)        
        csv_data = dict_to_csv_string(flat_data)
        
        # 3. Armamos la respuesta unificada para el endpoint
        return {
            "json_data": json_data,
            "csv_data": csv_data
        }