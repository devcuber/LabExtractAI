from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class LabExtractionStatus(StrEnum):
    """Estados permitidos para una solicitud de extracción."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LabExtractionRequestCreate(BaseModel):
    """Datos listos para insertar una solicitud de extracción."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    file_content: bytes
    mime_type: str
    original_filename: str


class LabExtractionRequest(BaseModel):
    """Representación completa de una fila de lab_extraction_requests."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    file_content: bytes
    mime_type: str
    original_filename: str
    status: LabExtractionStatus
    result_json: dict[str, Any] | list[Any] | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class LabExtractionRequestListItem(BaseModel):
    """Vista ligera de una solicitud para el listado de la cola."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    original_filename: str
    mime_type: str
    status: LabExtractionStatus
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None


class LabExtractionRequestUpdate(BaseModel):
    """Campos permitidos para actualizar una solicitud de extracción."""

    model_config = ConfigDict(extra="forbid")

    status: LabExtractionStatus | None = None
    result_json: dict[str, Any] | list[Any] | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "LabExtractionRequestUpdate":
        if not self.model_fields_set:
            raise ValueError("Se debe proporcionar al menos un campo para actualizar.")
        return self
