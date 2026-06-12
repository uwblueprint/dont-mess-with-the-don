from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.registration import Registration, RegistrationCreate, RegistrationUpdate


class IRegistrationService(ABC):
    """Interface to handle CRUD functionality for registrations"""

    @abstractmethod
    async def get_registrations(self, session: AsyncSession) -> list[Registration]:
        pass

    @abstractmethod
    async def get_registration(
        self, session: AsyncSession, registration_id: int
    ) -> Registration | None:
        pass

    @abstractmethod
    async def create_registration(
        self, session: AsyncSession, registration_data: RegistrationCreate
    ) -> Registration:
        pass

    @abstractmethod
    async def update_registration(
        self,
        session: AsyncSession,
        registration_id: int,
        registration_data: RegistrationUpdate,
    ) -> Registration | None:
        pass
