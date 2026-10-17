import asyncio
import json
import logging
import time
from uuid import UUID

from core.base_llm_provider import BaseLLMProvider
from models.lab_extraction_request import (
    LabExtractionRequest,
    LabExtractionRequestCreate,
    LabExtractionRequestListItem,
    LabExtractionRequestUpdate,
    LabExtractionStatus,
)
from repositories.i_repository import IRepository
from transformers.fhir_tabular_transformer import FHIRTabularTransformer
from utils.csv_utils import list_to_csv_string
from utils.file_utils import FileTypeDetector, UnsupportedFileTypeError
from utils.pdf_utils import PdfUtils


logger = logging.getLogger(__name__)


class ExtractionRequestNotFoundError(Exception):
    """La solicitud de extracción no existe."""


class ExtractionResultNotReadyError(Exception):
    def __init__(self, status: LabExtractionStatus) -> None:
        self.status = status
        super().__init__(f"La extracción aún no está completada: {status.value}.")


class ExtractionRequestFailedError(Exception):
    def __init__(self, error_message: str | None) -> None:
        self.error_message = error_message
        super().__init__("La extracción falló.")


class ExtractionResultMissingError(Exception):
    """Una solicitud completada no contiene resultado persistido."""


class LabAnalyzerService:
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        extraction_request_repository: IRepository[
            LabExtractionRequest,
            LabExtractionRequestCreate,
            LabExtractionRequestUpdate,
            UUID,
            LabExtractionRequestListItem,
        ],
    ):
        self.llm = llm_provider
        self.extraction_request_repository = extraction_request_repository
        self.file_type_detector = FileTypeDetector()

    async def extract_data(self, file_content: bytes, mime_type: str) -> dict:
        prompt = "Analyze the attached laboratory report and extract all test results into the FHIR Observation format."

        # Pasamos el mime_type real (PDF o imagen) al provider
        response_text = await asyncio.to_thread(self.llm.ask, prompt, file_content, mime_type)
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
        csv_data = list_to_csv_string(vertical_rows, write_header=False)
        
        elapsed = time.perf_counter() - step_time
        logger.info(f"[PERF] 4. Transformación a CSV completada en {elapsed:.4f}s")

        # Tiempo total acumulado
        total_elapsed = time.perf_counter() - start_total_time
        logger.info(f"[PERF] === Flujo completo finalizado en {total_elapsed:.4f}s ===")
        
        return {
            "json_data": json_data,
            "csv_data": csv_data
        }

    async def prepare_file_for_queue(
        self,
        file_content: bytes,
        original_filename: str | None,
        password: str | None = None,
    ) -> tuple[bytes, str, str]:
        """Valida y prepara un archivo para persistirlo en la cola."""
        if not original_filename or not original_filename.strip():
            raise ValueError("El archivo debe incluir un nombre original.")
        if not file_content:
            raise ValueError("El archivo está vacío.")

        mime_type = self.file_type_detector.detect(file_content, original_filename, None)
        if not self.file_type_detector.is_allowed(mime_type):
            raise UnsupportedFileTypeError(
                "Formato no soportado. Sube un PDF, PNG, JPG o WEBP."
            )

        if PdfUtils.is_pdf(file_content):
            file_content = PdfUtils.unlock_pdf(file_content, password)

        return file_content, mime_type, original_filename.strip()

    async def enqueue_for_extraction(
        self,
        file_content: bytes,
        original_filename: str | None,
        password: str | None = None,
    ) -> LabExtractionRequest:
        """Prepara el archivo y crea una solicitud pendiente de extracción."""
        prepared_content, mime_type, validated_filename = await self.prepare_file_for_queue(
            file_content=file_content,
            original_filename=original_filename,
            password=password,
        )
        request = LabExtractionRequestCreate(
            file_content=prepared_content,
            mime_type=mime_type,
            original_filename=validated_filename,
        )
        return await self.extraction_request_repository.create(request)

    async def get_extraction_result(self, request_id: UUID) -> dict | list:
        """Obtiene el resultado FHIR de una solicitud completada."""
        request = await self.extraction_request_repository.get_by_id(request_id)
        if request is None:
            raise ExtractionRequestNotFoundError()
        if request.status in (LabExtractionStatus.PENDING, LabExtractionStatus.PROCESSING):
            raise ExtractionResultNotReadyError(request.status)
        if request.status == LabExtractionStatus.FAILED:
            raise ExtractionRequestFailedError(request.error_message)
        if request.result_json is None:
            raise ExtractionResultMissingError()
        return request.result_json

    async def get_extraction_csv(self, request_id: UUID) -> tuple[str, str]:
        """Genera el CSV descargable desde el resultado FHIR persistido."""
        request = await self.extraction_request_repository.get_by_id(request_id)
        if request is None:
            raise ExtractionRequestNotFoundError()
        if request.status in (LabExtractionStatus.PENDING, LabExtractionStatus.PROCESSING):
            raise ExtractionResultNotReadyError(request.status)
        if request.status == LabExtractionStatus.FAILED:
            raise ExtractionRequestFailedError(request.error_message)
        if request.result_json is None:
            raise ExtractionResultMissingError()

        vertical_rows = FHIRTabularTransformer.observation_to_vertical_rows(request.result_json)
        csv_data = list_to_csv_string(vertical_rows, write_header=False)
        return csv_data, request.original_filename

    async def list_extraction_requests(self) -> list[LabExtractionRequestListItem]:
        """Obtiene la lista completa de solicitudes de extracción ordenadas por fecha de creación."""
        return await self.extraction_request_repository.list()