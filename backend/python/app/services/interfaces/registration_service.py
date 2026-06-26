from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enum import RegistrationStatusEnum
from app.models.registration import Registration, RegistrationCreate, RegistrationUpdate


class IRegistrationService(ABC):
    """Interface to handle CRUD functionality for registrations"""

    @abstractmethod
    async def get_registrations(
        self,
        session: AsyncSession,
        user_id: int | None = None,
        event_instance_id: UUID | None = None,
        status: RegistrationStatusEnum | None = None,
    ) -> list[Registration]:
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

    @abstractmethod
    async def delete_registration(self, session: AsyncSession, registration_id: int) -> bool:
        pass
