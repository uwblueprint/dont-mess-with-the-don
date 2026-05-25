from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity, EntityCreate, EntityUpdate


class IEntityService(ABC):
    """
    A class to handle CRUD functionality for entities
    """

    @abstractmethod
    async def get_entities(self, session: AsyncSession) -> list[Entity]:
        pass

    @abstractmethod
    async def get_entity(self, session: AsyncSession, entity_id: int) -> Entity | None:
        pass

    @abstractmethod
    async def create_entity(self, session: AsyncSession, entity_data: EntityCreate) -> Entity:
        pass

    @abstractmethod
    async def update_entity(
        self, session: AsyncSession, entity_id: int, entity_data: EntityUpdate
    ) -> Entity | None:
        pass

    @abstractmethod
    async def delete_entity(self, session: AsyncSession, entity_id: int) -> bool:
        pass
