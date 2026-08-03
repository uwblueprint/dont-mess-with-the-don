from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_type import EventType, EventTypeCreate, EventTypeUpdate


class IEventTypeService(ABC):
    """Interface for event type service"""

    @abstractmethod
    async def get_event_types(self, session: AsyncSession) -> list[EventType]:
        pass

    @abstractmethod
    async def get_event_type(self, session: AsyncSession, event_type_id: UUID) -> EventType | None:
        pass

    @abstractmethod
    async def create_event_type(
        self, session: AsyncSession, event_type_data: EventTypeCreate
    ) -> EventType:
        pass

    @abstractmethod
    async def update_event_type(
        self, session: AsyncSession, event_type_id: UUID, event_type_data: EventTypeUpdate
    ) -> EventType | None:
        pass

    @abstractmethod
    async def delete_event_type(self, session: AsyncSession, event_type_id: UUID) -> bool:
        pass
