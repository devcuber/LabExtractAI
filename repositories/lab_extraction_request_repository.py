from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from models.lab_extraction_request import (
    LabExtractionRequest,
    LabExtractionRequestCreate,
    LabExtractionRequestListItem,
    LabExtractionRequestUpdate,
    LabExtractionStatus,
)
from repositories.i_repository import IRepository


class LabExtractionRequestRepository(
    IRepository[
        LabExtractionRequest,
        LabExtractionRequestCreate,
        LabExtractionRequestUpdate,
        UUID,
        LabExtractionRequestListItem,
    ]
):
    """Repositorio PostgreSQL para la cola lab_extraction_requests."""

    _FULL_COLUMNS = """
        id,
        user_id,
        file_content,
        mime_type,
        original_filename,
        status,
        result_json,
        error_message,
        created_at,
        completed_at
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create(self, data: LabExtractionRequestCreate) -> LabExtractionRequest:
        query = f"""
            INSERT INTO lab_extraction_requests (
                user_id,
                file_content,
                mime_type,
                original_filename,
                status
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING {self._FULL_COLUMNS};
        """

        async with self._pool.connection() as connection:
            try:
                async with connection.cursor(row_factory=dict_row) as cursor:
                    await cursor.execute(
                        query,
                        (
                            data.user_id,
                            data.file_content,
                            data.mime_type,
                            data.original_filename,
                            LabExtractionStatus.PENDING.value,
                        ),
                    )
                    row = await cursor.fetchone()
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

        return LabExtractionRequest.model_validate(row)

    async def get_by_id(self, entity_id: UUID, user_id: UUID | None = None) -> LabExtractionRequest | None:
        query = f"""
            SELECT {self._FULL_COLUMNS}
            FROM lab_extraction_requests
            WHERE id = %s
              AND (%s::uuid IS NULL OR user_id = %s::uuid);
        """

        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, (entity_id, user_id, user_id))
                row = await cursor.fetchone()

        return LabExtractionRequest.model_validate(row) if row else None

    async def claim_pending(self, entity_id: UUID) -> LabExtractionRequest | None:
        """Cambia atómicamente una solicitud pending a processing y la devuelve."""
        query = f"""
            UPDATE lab_extraction_requests
            SET status = %s
            WHERE id = %s AND status = %s
            RETURNING {self._FULL_COLUMNS};
        """

        async with self._pool.connection() as connection:
            try:
                async with connection.cursor(row_factory=dict_row) as cursor:
                    await cursor.execute(
                        query,
                        (
                            LabExtractionStatus.PROCESSING.value,
                            entity_id,
                            LabExtractionStatus.PENDING.value,
                        ),
                    )
                    row = await cursor.fetchone()
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

        return LabExtractionRequest.model_validate(row) if row else None

    async def reset_recent_processing_to_pending(self) -> None:
        """Recupera solicitudes interrumpidas durante las últimas 24 horas."""
        query = """
            UPDATE lab_extraction_requests
            SET status = %s
            WHERE status = %s
              AND created_at >= NOW() - INTERVAL '24 hours';
        """

        async with self._pool.connection() as connection:
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        query,
                        (LabExtractionStatus.PENDING.value, LabExtractionStatus.PROCESSING.value),
                    )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

    async def list_recent_pending_ids(self) -> list[UUID]:
        """Devuelve los pending recuperables en orden cronológico FIFO."""
        query = """
            SELECT id
            FROM lab_extraction_requests
            WHERE status = %s
              AND created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY created_at ASC;
        """

        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, (LabExtractionStatus.PENDING.value,))
                rows = await cursor.fetchall()

        return [row["id"] for row in rows]

    async def list(self, user_id: UUID) -> list[LabExtractionRequestListItem]:
        query = """
            SELECT
                id,
                original_filename,
                mime_type,
                status,
                created_at,
                completed_at,
                error_message
            FROM lab_extraction_requests
            WHERE user_id = %s
            ORDER BY created_at DESC;
        """

        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, (user_id,))
                rows = await cursor.fetchall()

        return [LabExtractionRequestListItem.model_validate(row) for row in rows]

    async def update(
        self,
        entity_id: UUID,
        data: LabExtractionRequestUpdate,
    ) -> LabExtractionRequest | None:
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise ValueError("Se debe proporcionar al menos un campo para actualizar.")

        assignments: list[str] = []
        values: list[object] = []
        for field_name in ("status", "result_json", "completed_at", "error_message"):
            if field_name not in changes:
                continue

            assignments.append(f"{field_name} = %s")
            value = changes[field_name]
            if field_name == "status" and value is not None:
                value = value.value
            elif field_name == "result_json" and value is not None:
                value = Jsonb(value)
            values.append(value)

        query = f"""
            UPDATE lab_extraction_requests
            SET {', '.join(assignments)}
            WHERE id = %s
            RETURNING {self._FULL_COLUMNS};
        """
        values.append(entity_id)

        async with self._pool.connection() as connection:
            try:
                async with connection.cursor(row_factory=dict_row) as cursor:
                    await cursor.execute(query, values)
                    row = await cursor.fetchone()
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

        return LabExtractionRequest.model_validate(row) if row else None

    async def delete(self, entity_id: UUID) -> bool:
        query = """
            DELETE FROM lab_extraction_requests
            WHERE id = %s
            RETURNING id;
        """

        async with self._pool.connection() as connection:
            try:
                async with connection.cursor(row_factory=dict_row) as cursor:
                    await cursor.execute(query, (entity_id,))
                    row = await cursor.fetchone()
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

        return row is not None
