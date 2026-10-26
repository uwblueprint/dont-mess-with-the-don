import logging
from calendar import monthrange
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.attendance import Attendance
from app.models.confirmation_requests import (
    ConfirmationRequest,
    ConfirmationRequestCreate,
    ConfirmationRequestUpdate,
)
from app.models.enum import ConfirmationRequestStatusEnum, RegistrationStatusEnum
from app.models.event import Event
from app.models.registration import Registration
from app.services.interfaces.confirmation_request_service import IConfirmationRequestService

MIN_STRIKES_FOR_CONFIRMATION = 2
CONFIRMATION_DEADLINE_HOURS_BEFORE_EVENT = 72


class RegistrationNotFoundError(ValueError):
    """The registration referenced by a confirmation request does not exist."""


class ConfirmationRequestAlreadyExistsError(ValueError):
    """A registration already has a confirmation request."""


class ConfirmationRequestService(IConfirmationRequestService):
    """Service for managing confirmation requests"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

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

    async def requires_positive_confirmation(
        self, session: AsyncSession, user_id: int, as_of: datetime | None = None
    ) -> bool:
        """Return whether a user has two no-shows in the previous three months."""
        as_of = (as_of or datetime.now(ZoneInfo("America/Toronto"))).replace(tzinfo=None)
        month = as_of.month - 3
        year = as_of.year
        if month <= 0:
            month += 12
            year -= 1
        cutoff = as_of.replace(
            year=year,
            month=month,
            day=min(as_of.day, monthrange(year, month)[1]),
        )

        statement = (
            select(func.count(col(Registration.id)))
            .join(Event, col(Event.id) == col(Registration.event_instance_id))
            .outerjoin(
                Attendance,
                and_(
                    col(Attendance.user_id) == col(Registration.user_id),
                    col(Attendance.event_instance_id) == col(Registration.event_instance_id),
                ),
            )
            .where(
                col(Registration.user_id) == user_id,
                col(Registration.status) == RegistrationStatusEnum.ACCEPTED,
                col(Event.end_datetime) >= cutoff,
                col(Event.end_datetime) < as_of,
                col(Attendance.id).is_(None),
            )
        )
        result = await session.execute(statement)
        return result.scalar_one() >= MIN_STRIKES_FOR_CONFIRMATION

    async def add_for_registration_if_required(
        self, session: AsyncSession, registration: Registration
    ) -> None:
        """Stage a pending request for an eligible signup in its registration transaction."""
        if not await self.requires_positive_confirmation(session, registration.user_id):
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
                deadline=event.start_datetime
                - timedelta(hours=CONFIRMATION_DEADLINE_HOURS_BEFORE_EVENT),
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
