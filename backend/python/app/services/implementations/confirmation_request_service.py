import logging
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.confirmation_requests import (
    ConfirmationRequest,
    ConfirmationRequestCreate,
    ConfirmationRequestUpdate,
)
from app.models.enum import ConfirmationRequestStatusEnum
from app.models.event import Event
from app.models.registration import Registration
from app.services.implementations.strike_service import StrikeService
from app.services.interfaces.confirmation_request_service import IConfirmationRequestService

CONFIRMATION_DEADLINE_HOURS_BEFORE_EVENT = 72
MIN_CONFIRMATION_WINDOW_HOURS = 24


def calculate_confirmation_deadline(event_start: datetime, signed_up_at: datetime) -> datetime:
    """Deadline for a confirmation request.

    Normally 72h before the event. Late signups get at least 24h after signing up
    instead, so the deadline is never already passed, but it is never later than
    the event start.
    """
    deadline = max(
        event_start - timedelta(hours=CONFIRMATION_DEADLINE_HOURS_BEFORE_EVENT),
        signed_up_at + timedelta(hours=MIN_CONFIRMATION_WINDOW_HOURS),
    )
    return min(deadline, event_start)


class RegistrationNotFoundError(ValueError):
    """The registration referenced by a confirmation request does not exist."""


class ConfirmationRequestAlreadyExistsError(ValueError):
    """A registration already has a confirmation request."""


class ConfirmationRequestService(IConfirmationRequestService):
    """Service for managing confirmation requests"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.strike_service = StrikeService(logger)

    async def get_confirmation_requests(
        self, session: AsyncSession, event_id: UUID | None = None
    ) -> list[ConfirmationRequest]:
        """Get confirmation requests, optionally filtered by event."""
        try:
            statement = select(ConfirmationRequest)
            if event_id is not None:
                registration_ids = select(Registration.id).where(
                    Registration.event_instance_id == event_id
                )
                statement = statement.where(
                    col(ConfirmationRequest.registration_id).in_(registration_ids)
                )
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

    async def add_for_registration_if_required(
        self, session: AsyncSession, registration: Registration
    ) -> None:
        """Stage a pending request for an eligible signup in its registration transaction."""
        if not await self.strike_service.requires_confirmation(session, registration.user_id):
            return

        event = await session.get(Event, registration.event_instance_id)
        if event is None:
            raise ValueError(f"Event {registration.event_instance_id} does not exist")
        if registration.id is None:
            raise ValueError("Registration must be flushed before creating a confirmation request")

        session.add(
            ConfirmationRequest(
                registration_id=registration.id,
                email_status=ConfirmationRequestStatusEnum.PENDING,
                deadline=calculate_confirmation_deadline(
                    event_start=event.start_datetime,
                    signed_up_at=registration.created_at
                    or datetime.now(ZoneInfo("America/Toronto")).replace(tzinfo=None),
                ),
            )
        )

    async def create_confirmation_request(
        self, session: AsyncSession, data: ConfirmationRequestCreate
    ) -> ConfirmationRequest:
        """Create a new confirmation request"""
        try:
            statement = select(Registration.id).where(Registration.id == data.registration_id)
            result = await session.execute(statement)
            if result.scalar_one_or_none() is None:
                raise RegistrationNotFoundError(
                    f"Registration {data.registration_id} does not exist"
                )

            confirmation_request = ConfirmationRequest(**data.model_dump())
            session.add(confirmation_request)
            await session.commit()
            await session.refresh(confirmation_request)
            return confirmation_request
        except RegistrationNotFoundError:
            await session.rollback()
            raise
        except IntegrityError as error:
            await session.rollback()
            existing_request = await session.execute(
                select(ConfirmationRequest.id).where(
                    ConfirmationRequest.registration_id == data.registration_id
                )
            )
            if existing_request.scalar_one_or_none() is not None:
                raise ConfirmationRequestAlreadyExistsError(
                    f"Registration {data.registration_id} already has a confirmation request"
                ) from error

            registration = await session.execute(
                select(Registration.id).where(Registration.id == data.registration_id)
            )
            if registration.scalar_one_or_none() is None:
                raise RegistrationNotFoundError(
                    f"Registration {data.registration_id} does not exist"
                ) from error

            self.logger.error(f"Failed to create confirmation request: {error!s}")
            raise
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
