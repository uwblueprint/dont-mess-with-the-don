import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.registration import Registration, RegistrationCreate, RegistrationUpdate
from app.services.interfaces.registration_service import IRegistrationService


class RegistrationService(IRegistrationService):
    """Service for managing registrations"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_registrations(self, session: AsyncSession) -> list[Registration]:
        """Get all registrations"""
        statement = select(Registration)
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
