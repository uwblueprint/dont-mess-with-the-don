import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.event_series import EventSeries, EventSeriesCreate, EventSeriesUpdate
from app.services.interfaces.event_series_service import IEventSeriesService


class EventSeriesService(IEventSeriesService):
    """Service for managing event series"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_event_series_list(self, session: AsyncSession) -> list[EventSeries]:
        """Get all event series"""
        statement = select(EventSeries)
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def get_event_series(
        self, session: AsyncSession, event_series_id: UUID
    ) -> EventSeries | None:
        """Get event series by ID"""
        statement = select(EventSeries).where(EventSeries.id == event_series_id)
        result = await session.execute(statement)
        event_series = result.scalars().first()

        if not event_series:
            self.logger.error(f"Event series with id {event_series_id} not found")
            return None

        return event_series

    async def create_event_series(
        self, session: AsyncSession, event_series_data: EventSeriesCreate
    ) -> EventSeries:
        """Create new event series"""
        try:
            event_series = EventSeries(**event_series_data.model_dump())
            session.add(event_series)
            await session.commit()
            await session.refresh(event_series)
            return event_series
        except Exception as error:
            self.logger.error(f"Failed to create event series: {error!s}")
            await session.rollback()
            raise error

    async def update_event_series(
        self, session: AsyncSession, event_series_id: UUID, event_series_data: EventSeriesUpdate
    ) -> EventSeries | None:
        """Update existing event series"""
        try:
            statement = select(EventSeries).where(EventSeries.id == event_series_id)
            result = await session.execute(statement)
            event_series = result.scalars().first()

            if not event_series:
                self.logger.error(f"Event series with id {event_series_id} not found")
                return None

            update_data = event_series_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(event_series, field, value)

            await session.commit()
            await session.refresh(event_series)
            return event_series
        except Exception as error:
            self.logger.error(f"Failed to update event series: {error!s}")
            await session.rollback()
            raise error

    async def delete_event_series(self, session: AsyncSession, event_series_id: UUID) -> bool:
        """Delete event series by ID"""
        try:
            statement = select(EventSeries).where(EventSeries.id == event_series_id)
            result = await session.execute(statement)
            event_series = result.scalars().first()

            if not event_series:
                self.logger.error(f"Event series with id {event_series_id} not found")
                return False

            await session.delete(event_series)
            await session.commit()
            return True
        except Exception as error:
            self.logger.error(f"Failed to delete event series: {error!s}")
            await session.rollback()
            raise error
