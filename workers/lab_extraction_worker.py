import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from models.lab_extraction_request import LabExtractionRequestUpdate, LabExtractionStatus
from repositories.lab_extraction_request_repository import LabExtractionRequestRepository
from services.lab_service import LabAnalyzerService


logger = logging.getLogger(__name__)


class LabExtractionWorker:
    """Consume solicitudes de extracción de forma secuencial desde una cola en memoria."""

    def __init__(
        self,
        queue: asyncio.Queue[UUID],
        repository: LabExtractionRequestRepository,
        lab_service: LabAnalyzerService,
    ) -> None:
        self._queue = queue
        self._repository = repository
        self._lab_service = lab_service

    async def run(self) -> None:
        """Procesa indefinidamente un UUID a la vez, en orden FIFO."""
        while True:
            request_id = await self._queue.get()
            try:
                await self.process(request_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error no controlado procesando solicitud %s", request_id)
            finally:
                self._queue.task_done()

    async def process(self, request_id: UUID) -> None:
        """Reclama una solicitud pending y persiste su resultado o error."""
        request = await self._repository.claim_pending(request_id)
        if request is None:
            logger.info("Solicitud %s omitida: no existe o ya no está pending", request_id)
            return

        try:
            result_json = await self._lab_service.extract_data(
                request.file_content,
                request.mime_type,
            )
            await self._repository.update(
                request.id,
                LabExtractionRequestUpdate(
                    status=LabExtractionStatus.COMPLETED,
                    result_json=result_json,
                    completed_at=datetime.now(timezone.utc),
                    error_message=None,
                ),
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.exception("Falló la extracción de la solicitud %s", request.id)
            await self._repository.update(
                request.id,
                LabExtractionRequestUpdate(
                    status=LabExtractionStatus.FAILED,
                    completed_at=datetime.now(timezone.utc),
                    error_message=str(error),
                ),
            )
