import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.event import Event, EventCreate, EventUpdate


class EventService:
    """Service for managing events"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_events(
        self,
        session: AsyncSession,
        status: str | None = None,
        event_type: UUID | None = None,
        location: str | None = None,
        starts_after: datetime | None = None,
        starts_before: datetime | None = None,
    ) -> list[Event]:
        """Get all events"""
        statement = select(Event)
        if status is not None:
            statement = statement.where(Event.event_status == status)
        if event_type is not None:
            statement = statement.where(Event.event_type_id == event_type)
        if location is not None:
            statement = statement.where(func.lower(Event.location) == location.lower())
        if starts_after is not None:
            statement = statement.where(Event.start_datetime >= starts_after)
        if starts_before is not None:
            statement = statement.where(Event.start_datetime <= starts_before)

        result = await session.execute(statement)
        return list(result.scalars().all())

    async def get_event(self, session: AsyncSession, event_id: UUID) -> Event | None:
        """Get event by ID"""
        statement = select(Event).where(Event.id == event_id)
        result = await session.execute(statement)
        event = result.scalars().first()

        if not event:
            self.logger.error(f"Event with id {event_id} not found")
            return None

        return event

    async def create_event(self, session: AsyncSession, event_data: EventCreate) -> Event:
        """Create new event"""
        try:
            event = Event(**event_data.model_dump())
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event
        except Exception as error:
            self.logger.error(f"Failed to create event: {error!s}")
            await session.rollback()
            raise error

    async def update_event(
        self, session: AsyncSession, event_id: UUID, event_data: EventUpdate
    ) -> Event | None:
        """Update existing event"""
        try:
            statement = select(Event).where(Event.id == event_id)
            result = await session.execute(statement)
            event = result.scalars().first()

            if not event:
                self.logger.error(f"Event with id {event_id} not found")
                return None

            update_data = event_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(event, field, value)

            await session.commit()
            await session.refresh(event)
            return event
        except Exception as error:
            self.logger.error(f"Failed to update event: {error!s}")
            await session.rollback()
            raise error

    async def delete_event(self, session: AsyncSession, event_id: UUID) -> bool:
        """Delete event by ID"""
        try:
            statement = select(Event).where(Event.id == event_id)
            result = await session.execute(statement)
            event = result.scalars().first()

            if not event:
                self.logger.error(f"Event with id {event_id} not found")
                return False

            await session.delete(event)
            await session.commit()
            return True
        except Exception as error:
            self.logger.error(f"Failed to delete event: {error!s}")
            await session.rollback()
            raise error
