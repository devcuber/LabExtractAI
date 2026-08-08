import json
import io
import csv
from core.base_llm_provider import BaseLLMProvider
from transformers.fhir_tabular_transformer import FHIRTabularTransformer
from utils.csv_utils import dict_to_csv_string
from utils.pdf_utils import PdfUtils
from utils.file_utils import FileTypeDetector, UnsupportedFileTypeError


class LabAnalyzerService:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider
        self.file_type_detector = FileTypeDetector()

    async def extract_data(self, file_content: bytes, mime_type: str) -> dict:
        prompt = """
        Act as an expert in HL7 FHIR R4. Analyze all laboratory tests 
        from the attached file and create a single FHIR Observation resource 
        that acts as a general panel. Use the component field to include all 
        quantitative and qualitative results found in the document. 
        Omit empty fields, do not use dataAbsentReason, and respond strictly 
        with pure JSON only, with no markdown code blocks or additional text.
        """

        # Pasamos el mime_type real (PDF o imagen) al provider
        response_text = self.llm.ask_with_file(prompt, file_content, mime_type)
        
        # Limpieza
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)


    async def extract_and_transform(self, file_content: bytes, password: str | None = None) -> dict:
        """
        Orquesta el flujo completo:
        1. Detecta y valida el mime_type real del archivo (PDF o imagen soportada).
        2. Si es un PDF protegido con contraseña, lo desbloquea.
        3. Envía el archivo (PDF o imagen) a extract_data para obtener el JSON del recurso FHIR.
        4. Pasa el JSON al aplanador para generar el CSV tabular dinámico.
        5. Retorna ambos resultados listos para ser consumidos por el endpoint.
        """
        # 1. Detectamos el mime_type real 
        mime_type = self.file_type_detector.detect(file_content, None, None)
        if not self.file_type_detector.is_allowed(mime_type):
            raise UnsupportedFileTypeError(
                "Formato no soportado. Sube un PDF, PNG, JPG o WEBP."
            )

        # 2. Si es un PDF protegido, lo desbloqueamos antes de enviarlo al LLM
        if PdfUtils.is_pdf(file_content):
            file_content = PdfUtils.unlock_pdf(file_content, password)

        # 3. Obtenemos el JSON estructurado desde el LLM usando el archivo y su mime_type real
        json_data = await self.extract_data(file_content, mime_type)

        # 4. Transformamos el JSON obtenido al formato CSV tabular FHIR
        flat_data = FHIRTabularTransformer.flatten_fhir_to_dict(json_data)
        csv_data = dict_to_csv_string(flat_data)

        # 5. Armamos la respuesta unificada para el endpoint
        return {
            "json_data": json_data,
            "csv_data": csv_data
        }