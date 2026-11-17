from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserCreate, UserRegister, UserUpdate


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
    async def get_user_by_firebase_uid(
        self, session: AsyncSession, firebase_uid: str
    ) -> User | None:
        pass

    @abstractmethod
    async def get_user_children(self, session: AsyncSession, user_id: int) -> list[User] | None:
        pass

    @abstractmethod
    async def create_user(self, session: AsyncSession, user_data: UserCreate) -> User:
        pass

    @abstractmethod
    async def register_user(
        self, session: AsyncSession, firebase_uid: str, email: str, user_data: UserRegister
    ) -> User:
        pass

    @abstractmethod
    async def update_user(
        self, session: AsyncSession, user_id: int, user_data: UserUpdate
    ) -> User | None:
        pass

    @abstractmethod
    async def delete_user(self, session: AsyncSession, user_id: int) -> bool:
        pass
