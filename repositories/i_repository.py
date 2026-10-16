from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TEntity = TypeVar("TEntity")
TCreate = TypeVar("TCreate")
TUpdate = TypeVar("TUpdate")
TId = TypeVar("TId")
TListItem = TypeVar("TListItem")


class IRepository(ABC, Generic[TEntity, TCreate, TUpdate, TId, TListItem]):
    """Contrato genérico para repositorios CRUD."""

    @abstractmethod
    async def create(self, data: TCreate) -> TEntity:
        """Crea una entidad y devuelve su representación completa."""

    @abstractmethod
    async def get_by_id(self, entity_id: TId) -> TEntity | None:
        """Obtiene una entidad completa por identificador."""

    @abstractmethod
    async def list(self) -> list[TListItem]:
        """Obtiene una lista ligera de entidades."""

    @abstractmethod
    async def update(self, entity_id: TId, data: TUpdate) -> TEntity | None:
        """Actualiza una entidad y devuelve su representación completa."""

    @abstractmethod
    async def delete(self, entity_id: TId) -> bool:
        """Elimina una entidad e indica si existía."""
