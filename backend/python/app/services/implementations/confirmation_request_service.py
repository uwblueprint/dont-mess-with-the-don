import logging
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.confirmation_requests import (
    ConfirmationRequest,
    ConfirmationRequestCreate,
    ConfirmationRequestUpdate,
)
from app.models.registration import Registration
from app.services.interfaces.confirmation_request_service import IConfirmationRequestService


class ConfirmationRequestService(IConfirmationRequestService):
    """Service for managing confirmation requests"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_confirmation_requests(self, session: AsyncSession) -> list[ConfirmationRequest]:
        """Get all confirmation requests"""
        try:
            statement = select(ConfirmationRequest)
            result = await session.execute(statement)
            return list(result.scalars().all())
        except Exception as error:
            self.logger.error(f"Failed to get confirmation requests: {error!s}")
            raise error

    async def get_confirmation_request(
        self, session: AsyncSession, request_id: UUID
    ) -> ConfirmationRequest | None:
        """Get a confirmation request by ID"""
        try:
            statement = select(ConfirmationRequest).where(ConfirmationRequest.id == request_id)
            result = await session.execute(statement)
            confirmation_request = result.scalars().first()

            if not confirmation_request:
                self.logger.warning(f"Confirmation request with id {request_id} not found")
                return None

            return confirmation_request
        except Exception as error:
            self.logger.error(f"Failed to get confirmation request {request_id}: {error!s}")
            raise error

    async def get_confirmation_requests_by_event(
        self, session: AsyncSession, event_id: UUID
    ) -> list[ConfirmationRequest]:
        """Get all confirmation requests for a given event via registration join"""
        try:
            registration_ids = select(Registration.id).where(
                Registration.event_instance_id == event_id
            )
            statement = select(ConfirmationRequest).where(
                ConfirmationRequest.registration_id.in_(registration_ids)  # type: ignore[attr-defined]
            )
            result = await session.execute(statement)
            return list(result.scalars().all())
        except Exception as error:
            self.logger.error(
                f"Failed to get confirmation requests for event {event_id}: {error!s}"
            )
            raise error

    async def create_confirmation_request(
        self, session: AsyncSession, data: ConfirmationRequestCreate
    ) -> ConfirmationRequest:
        """Create a new confirmation request"""
        try:
            confirmation_request = ConfirmationRequest(**data.model_dump())
            session.add(confirmation_request)
            await session.commit()
            await session.refresh(confirmation_request)
            return confirmation_request
        except Exception as error:
            self.logger.error(f"Failed to create confirmation request: {error!s}")
            await session.rollback()
            raise error

    async def update_confirmation_request(
        self, session: AsyncSession, request_id: UUID, data: ConfirmationRequestUpdate
    ) -> ConfirmationRequest | None:
        """Update an existing confirmation request"""
        try:
            statement = select(ConfirmationRequest).where(ConfirmationRequest.id == request_id)
            result = await session.execute(statement)
            confirmation_request = result.scalars().first()

            if not confirmation_request:
                self.logger.warning(f"Confirmation request with id {request_id} not found")
                return None

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(confirmation_request, field, value)

            confirmation_request.updated_at = datetime.now(ZoneInfo("America/Toronto")).replace(
                tzinfo=None
            )

            await session.commit()
            await session.refresh(confirmation_request)
            return confirmation_request
        except Exception as error:
            self.logger.error(f"Failed to update confirmation request {request_id}: {error!s}")
            await session.rollback()
            raise error

    async def delete_confirmation_request(self, session: AsyncSession, request_id: UUID) -> bool:
        """Delete a confirmation request by ID"""
        try:
            statement = select(ConfirmationRequest).where(ConfirmationRequest.id == request_id)
            result = await session.execute(statement)
            confirmation_request = result.scalars().first()

            if not confirmation_request:
                self.logger.warning(f"Confirmation request with id {request_id} not found")
                return False

            await session.delete(confirmation_request)
            await session.commit()
            return True
        except Exception as error:
            self.logger.error(f"Failed to delete confirmation request {request_id}: {error!s}")
            await session.rollback()
            raise error
