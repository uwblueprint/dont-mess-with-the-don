from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserCreate, UserUpdate


class IUserService(ABC):
    """A class to handle CRUD functionality for users"""

    @abstractmethod
    async def get_users(self, session: AsyncSession) -> list[User]:
        pass

    @abstractmethod
    async def get_user(self, session: AsyncSession, user_id: int) -> User | None:
        pass

    @abstractmethod
    async def get_user_by_email(self, session: AsyncSession, email: str) -> User | None:
        pass

    @abstractmethod
    async def create_user(self, session: AsyncSession, user_data: UserCreate) -> User:
        pass

    @abstractmethod
    async def update_user(
        self, session: AsyncSession, user_id: int, user_data: UserUpdate
    ) -> User | None:
        pass

    @abstractmethod
    async def delete_user(self, session: AsyncSession, user_id: int) -> bool:
        pass
