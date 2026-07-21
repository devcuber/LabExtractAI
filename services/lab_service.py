import json
from core.base_llm_provider import BaseLLMProvider

class LabAnalyzerService:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def extract_data(self, file_content: bytes) -> dict:
        prompt = """
        Actúa como un experto en HL7 FHIR R4. Crea un recurso 'Observation' 
        basado en el archivo adjunto. Omite campos vacíos, no uses dataAbsentReason, 
        responde solo con el JSON puro.
        """
        
        # Llamas al nuevo método del provider
        response_text = self.llm.ask_with_file(prompt, file_content)
        
        # Limpieza
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)