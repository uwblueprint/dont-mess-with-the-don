from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.confirmation_requests import (
    ConfirmationRequest,
    ConfirmationRequestCreate,
    ConfirmationRequestUpdate,
)


class IConfirmationRequestService(ABC):
    """A class to handle CRUD functionality for confirmation requests"""

    @abstractmethod
    async def get_confirmation_requests(self, session: AsyncSession) -> list[ConfirmationRequest]:
        pass

    @abstractmethod
    async def get_confirmation_request(
        self, session: AsyncSession, request_id: UUID
    ) -> ConfirmationRequest | None:
        pass

    @abstractmethod
    async def get_confirmation_requests_by_event(
        self, session: AsyncSession, event_id: UUID
    ) -> list[ConfirmationRequest]:
        pass

    @abstractmethod
    async def create_confirmation_request(
        self, session: AsyncSession, data: ConfirmationRequestCreate
    ) -> ConfirmationRequest:
        pass

    @abstractmethod
    async def update_confirmation_request(
        self, session: AsyncSession, request_id: UUID, data: ConfirmationRequestUpdate
    ) -> ConfirmationRequest | None:
        pass

    @abstractmethod
    async def delete_confirmation_request(self, session: AsyncSession, request_id: UUID) -> bool:
        pass
