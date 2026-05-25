from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simple_entity import SimpleEntity, SimpleEntityCreate, SimpleEntityUpdate


class ISimpleEntityService(ABC):
    """
    A class to handle CRUD functionality for simple entities
    """

    @abstractmethod
    async def get_simple_entities(self, session: AsyncSession) -> list[SimpleEntity]:
        pass

    @abstractmethod
    async def get_simple_entity(
        self, session: AsyncSession, simple_entity_id: int
    ) -> SimpleEntity | None:
        pass

    @abstractmethod
    async def create_simple_entity(
        self, session: AsyncSession, simple_entity_data: SimpleEntityCreate
    ) -> SimpleEntity:
        pass

    @abstractmethod
    async def update_simple_entity(
        self,
        session: AsyncSession,
        simple_entity_id: int,
        simple_entity_data: SimpleEntityUpdate,
    ) -> SimpleEntity | None:
        pass

    @abstractmethod
    async def delete_simple_entity(self, session: AsyncSession, simple_entity_id: int) -> bool:
        pass
