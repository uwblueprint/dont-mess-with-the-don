import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models.user import User, UserCreate, UserUpdate
from app.services.interfaces.user_service import IUserService


class UserService(IUserService):
    """Service for managing users"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_users(self, session: AsyncSession) -> list[User]:
        """Get all users"""
        statement = select(User)
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def get_user(self, session: AsyncSession, user_id: int) -> User | None:
        """Get user by ID"""
        statement = select(User).where(User.id == user_id)
        result = await session.execute(statement)
        user = result.scalars().first()

        if not user:
            self.logger.warning(f"User with id {user_id} not found")
            return None

        return user

    async def get_user_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Get user by email"""
        statement = select(User).where(User.email == email)
        result = await session.execute(statement)
        return result.scalars().first()

    async def get_user_children(self, session: AsyncSession, user_id: int) -> list[User] | None:
        """Get user by ID and return their children"""
        statement = (
            select(User).options(selectinload(User.children)).where(User.id == user_id)
        )
        result = await session.execute(statement)
        user = result.scalars().first()

        if not user:
            self.logger.warning(f"User with id {user_id} not found")
            return None

        return user.children

    async def create_user(self, session: AsyncSession, user_data: UserCreate) -> User:
        """Create new user"""
        try:
            user = User(**user_data.model_dump())
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
        except IntegrityError as error:
            await session.rollback()
            self.logger.warning(f"Duplicate email on create: {user_data.email}")
            raise ValueError(f"Email {user_data.email} is already in use") from error
        except Exception as error:
            self.logger.error(f"Failed to create user: {error!s}")
            await session.rollback()
            raise error

    async def update_user(
        self, session: AsyncSession, user_id: int, user_data: UserUpdate
    ) -> User | None:
        """Update existing user"""
        try:
            statement = select(User).where(User.id == user_id)
            result = await session.execute(statement)
            user = result.scalars().first()

            if not user:
                self.logger.warning(f"User with id {user_id} not found")
                return None

            update_data = user_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)

            user.updated_at = datetime.now(ZoneInfo("America/Toronto")).replace(tzinfo=None)

            await session.commit()
            await session.refresh(user)
            return user
        except Exception as error:
            self.logger.error(f"Failed to update user: {error!s}")
            await session.rollback()
            raise error

    async def delete_user(self, session: AsyncSession, user_id: int) -> bool:
        """Delete user by ID"""
        try:
            statement = select(User).where(User.id == user_id)
            result = await session.execute(statement)
            user = result.scalars().first()

            if not user:
                self.logger.warning(f"User with id {user_id} not found")
                return False

            await session.delete(user)
            await session.commit()
            return True
        except Exception as error:
            self.logger.error(f"Failed to delete user: {error!s}")
            await session.rollback()
            raise error
