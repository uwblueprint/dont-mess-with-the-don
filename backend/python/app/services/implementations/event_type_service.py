import logging


from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.event_type import EventType, EventTypeCreate, EventTypeUpdate


class EventTypeService:
    """Service for managing event types"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_event_types(self, session: AsyncSession) -> list[EventType]:
        """Get all event types"""
        statement = select(EventType)
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def get_event_type(self, session: AsyncSession, event_type_id: int) -> EventType | None:
        """Get event type by ID"""
        statement = select(EventType).where(EventType.id == event_type_id)
        result = await session.execute(statement)
        event_type = result.scalars().first()

        if not event_type:
            self.logger.error(f"Event type with id {event_type_id} not found")
            return None

        return event_type

    async def create_event_type(self, session: AsyncSession, event_type_data: EventTypeCreate) -> EventType:
        """Create new event type"""
        try:
            event_type = EventType(**event_type_data.model_dump())
            session.add(event_type)
            await session.commit()
            await session.refresh(event_type)
            return event_type
        except Exception as error:
            self.logger.error(f"Failed to create event type: {error!s}")
            await session.rollback()
            raise error

    async def update_event_type(
        self, session: AsyncSession, event_type_id: int, event_type_data: EventTypeUpdate
    ) -> EventType | None:
        """Update existing event type"""
        try:
            statement = select(EventType).where(EventType.id == event_type_id)
            result = await session.execute(statement)
            event_type = result.scalars().first()

            if not event_type:
                self.logger.error(f"Event type with id {event_type_id} not found")
                return None

            update_data = event_type_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(event_type, field, value)

            await session.commit()
            await session.refresh(event_type)
            return event_type
        except Exception as error:
            self.logger.error(f"Failed to update event type: {error!s}")
            await session.rollback()
            raise error

    async def delete_event_type(self, session: AsyncSession, event_type_id: int) -> bool:
        """Delete event type by ID"""
        try:
            statement = select(EventType).where(EventType.id == event_type_id)
            result = await session.execute(statement)
            event_type = result.scalars().first()

            if not event_type:
                self.logger.error(f"Event type with id {event_type_id} not found")
                return False

            await session.delete(event_type)
            await session.commit()
            return True
        except Exception as error:
            self.logger.error(f"Failed to delete event type: {error!s}")
            await session.rollback()
            raise error
