import logging
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.enum import RegistrationStatusEnum
from app.models.registration import Registration, RegistrationCreate, RegistrationUpdate
from app.services.interfaces.registration_service import IRegistrationService


class RegistrationService(IRegistrationService):
    """Service for managing registrations"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_registrations(
        self,
        session: AsyncSession,
        user_id: int | None = None,
        event_instance_id: UUID | None = None,
        status: RegistrationStatusEnum | None = None,
    ) -> list[Registration]:
        """Get all registrations, optionally filtered"""
        statement = select(Registration)
        if user_id is not None:
            statement = statement.where(Registration.user_id == user_id)
        if event_instance_id is not None:
            statement = statement.where(Registration.event_instance_id == event_instance_id)
        if status is not None:
            statement = statement.where(Registration.status == status)

        result = await session.execute(statement)
        return list(result.scalars().all())

    async def get_registration(
        self, session: AsyncSession, registration_id: int
    ) -> Registration | None:
        """Get registration by ID"""
        statement = select(Registration).where(Registration.id == registration_id)
        result = await session.execute(statement)
        registration = result.scalars().first()

        if not registration:
            self.logger.warning(f"Registration with id {registration_id} not found")
            return None

        return registration

    async def create_registration(
        self, session: AsyncSession, registration_data: RegistrationCreate
    ) -> Registration:
        """Create new registration"""
        try:
            registration = Registration(**registration_data.model_dump())
            session.add(registration)
            await session.commit()
            await session.refresh(registration)
            return registration
        except Exception as error:
            self.logger.error(f"Failed to create registration: {error!s}")
            await session.rollback()
            raise error

    async def update_registration(
        self,
        session: AsyncSession,
        registration_id: int,
        registration_data: RegistrationUpdate,
    ) -> Registration | None:
        """Update existing registration"""
        try:
            statement = select(Registration).where(Registration.id == registration_id)
            result = await session.execute(statement)
            registration = result.scalars().first()

            if not registration:
                self.logger.warning(f"Registration with id {registration_id} not found")
                return None

            # Enforce status transitions: waitlist -> accepted -> cancelled
            if (
                registration_data.status is not None
                and registration_data.status != registration.status
            ):
                allowed_transitions = {
                    RegistrationStatusEnum.WAITLIST: {RegistrationStatusEnum.ACCEPTED},
                    RegistrationStatusEnum.ACCEPTED: {RegistrationStatusEnum.CANCELLED},
                    RegistrationStatusEnum.CANCELLED: set(),
                }
                allowed = allowed_transitions.get(registration.status, set())
                if registration_data.status not in allowed:
                    raise ValueError(
                        f"Cannot transition status from {registration.status.value} "
                        f"to {registration_data.status.value}"
                    )

            update_data = registration_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(registration, field, value)

            registration.updated_at = datetime.now(ZoneInfo("America/Toronto")).replace(tzinfo=None)

            await session.commit()
            await session.refresh(registration)
            return registration
        except Exception as error:
            self.logger.error(f"Failed to update registration: {error!s}")
            await session.rollback()
            raise error

    async def delete_registration(self, session: AsyncSession, registration_id: int) -> bool:
        """Delete registration by ID"""
        try:
            statement = select(Registration).where(Registration.id == registration_id)
            result = await session.execute(statement)
            registration = result.scalars().first()

            if not registration:
                self.logger.warning(f"Registration with id {registration_id} not found")
                return False

            await session.delete(registration)
            await session.commit()
            return True
        except Exception as error:
            self.logger.error(f"Failed to delete registration: {error!s}")
            await session.rollback()
            raise error
