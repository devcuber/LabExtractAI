import json
import logging
import time
from core.base_llm_provider import BaseLLMProvider
from transformers.fhir_tabular_transformer import FHIRTabularTransformer
from utils.csv_utils import list_to_csv_string
from utils.pdf_utils import PdfUtils
from utils.file_utils import FileTypeDetector, UnsupportedFileTypeError


logger = logging.getLogger(__name__)

class LabAnalyzerService:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider
        self.file_type_detector = FileTypeDetector()
        system_prompt = """
        You are an expert in HL7 FHIR R4, specialized in clinical laboratory data structures.
        Your sole purpose is to analyze medical laboratory reports and map them into a single 
        valid FHIR Observation resource acting as a general panel.

        STRICT RULES:
        1. Use the 'component' field to include all quantitative and qualitative results found in the document.
        2. Omit empty fields completely.
        3. NEVER use dataAbsentReason.
        """
        self.llm.set_system_instruction(system_prompt)

    async def extract_data(self, file_content: bytes, mime_type: str) -> dict:
        prompt = "Analyze the attached laboratory report and extract all test results into the FHIR Observation format."

        # Pasamos el mime_type real (PDF o imagen) al provider
        response_text = self.llm.ask_with_file(prompt, file_content, mime_type)
        return json.loads(response_text)

    async def extract_and_transform(self, file_content: bytes, password: str | None = None) -> dict:
        """
        Orquesta el flujo completo:
        1. Detecta y valida el mime_type real del archivo (PDF o imagen soportada).
        2. Si es un PDF protegido con contraseña, lo desbloquea.
        3. Envía el archivo (PDF o imagen) a extract_data para obtener el JSON del recurso FHIR.
        4. Pasa el JSON al aplanador para generar el CSV tabular dinámico.
        5. Retorna ambos resultados listos para ser consumidos por el endpoint.
        """
        if not file_content:
            raise ValueError("El archivo está vacío.")

        # Iniciamos el cronómetro global
        start_total_time = time.perf_counter()
        step_time = start_total_time

        # 1. Detectamos y validamos el mime_type real
        mime_type = self.file_type_detector.detect(file_content, None, None)
        if not self.file_type_detector.is_allowed(mime_type):
            raise UnsupportedFileTypeError(
                "Formato no soportado. Sube un PDF, PNG, JPG o WEBP."
            )
        
        elapsed = time.perf_counter() - step_time
        logger.info(f"[PERF] 1. Detección y validación de tipo completada en {elapsed:.4f}s (mime: {mime_type})")
        step_time = time.perf_counter()

        # 2. Si es un PDF protegido, lo desbloqueamos
        if PdfUtils.is_pdf(file_content):
            logger.info("El usuario subió un archivo reconocido como PDF.")            
            file_content = PdfUtils.unlock_pdf(file_content, password)
            
            elapsed = time.perf_counter() - step_time
            logger.info(f"[PERF] 2. Desbloqueo de PDF completado en {elapsed:.4f}s")
            step_time = time.perf_counter()

        # 3. Envía el archivo al LLM (Gemini)
        json_data = await self.extract_data(file_content, mime_type)
        
        elapsed = time.perf_counter() - step_time
        logger.info(f"[PERF] 3. Extracción de datos con Gemini completada en {elapsed:.4f}s")
        step_time = time.perf_counter()

        # 4. Aplanamiento y transformación a CSV
        vertical_rows = FHIRTabularTransformer.observation_to_vertical_rows(json_data)        
        csv_data = list_to_csv_string(vertical_rows)
        
        elapsed = time.perf_counter() - step_time
        logger.info(f"[PERF] 4. Transformación a CSV completada en {elapsed:.4f}s")

        # Tiempo total acumulado
        total_elapsed = time.perf_counter() - start_total_time
        logger.info(f"[PERF] === Flujo completo finalizado en {total_elapsed:.4f}s ===")
        
        return {
            "json_data": json_data,
            "csv_data": csv_data
        }