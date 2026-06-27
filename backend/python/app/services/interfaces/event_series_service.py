from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_series import EventSeries, EventSeriesCreate, EventSeriesUpdate


class IEventSeriesService(ABC):
    """A class to handle CRUD functionality for event series"""

    @abstractmethod
    async def get_event_series_list(self, session: AsyncSession) -> list[EventSeries]:
        pass

    @abstractmethod
    async def get_event_series(self, session: AsyncSession, event_series_id: UUID) -> EventSeries | None:
        pass

    @abstractmethod
    async def create_event_series(
        self, session: AsyncSession, event_series_data: EventSeriesCreate
    ) -> EventSeries:
        pass

    @abstractmethod
    async def update_event_series(
        self, session: AsyncSession, event_series_id: UUID, event_series_data: EventSeriesUpdate
    ) -> EventSeries | None:
        pass

    @abstractmethod
    async def delete_event_series(self, session: AsyncSession, event_series_id: UUID) -> bool:
        pass
