from urllib.parse import urlparse

from pydantic import EmailStr, field_validator
from sqlalchemy import Column, Enum as SAEnum, String
from sqlmodel import Field, SQLModel

from .base import BaseModel
from .enum import UserProfileType, UserProvider


class UserBase(SQLModel):
    """Shared fields between table and API models"""

    email: EmailStr = Field(sa_column=Column(String, unique=True, nullable=False))
    provider_id: str | None = Field(default=None, max_length=255)
    provider: UserProvider | None = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                UserProvider,
                values_callable=lambda obj: [e.value for e in obj],
                name="userprovider",
                create_type=True,
            ),
            nullable=True,
        ),
    )
    profile_pic_url: str | None = Field(default=None, max_length=500)

    @field_validator("profile_pic_url")
    @classmethod
    def validate_profile_pic_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("must be a valid HTTP or HTTPS URL")
        return v

    profile_type: UserProfileType = Field(
        default=UserProfileType.DEFAULT,
        sa_column=Column(
            SAEnum(
                UserProfileType,
                values_callable=lambda obj: [e.value for e in obj],
                name="userprofiletype",
                create_type=True,
            )
        ),
    )
    location: str | None = Field(default=None, max_length=255)
    is_deactivated: bool = Field(default=False)
    parent_id: int | None = Field(default=None, foreign_key="users.id")


class User(UserBase, BaseModel, table=True):
    """User model"""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    password_hash: str | None = Field(default=None)


class UserCreate(UserBase):
    """User creation request"""

    password_hash: str | None = Field(default=None)


class UserRead(UserBase):
    """User response model - password_hash intentionally excluded"""

    id: int


class UserUpdate(SQLModel):
    """User update request - all fields optional"""

    email: EmailStr | None = Field(default=None)
    provider_id: str | None = Field(default=None, max_length=255)
    provider: UserProvider | None = Field(default=None)
    profile_pic_url: str | None = Field(default=None, max_length=500)
    profile_type: UserProfileType | None = Field(default=None)
    location: str | None = Field(default=None, max_length=255)
    is_deactivated: bool | None = Field(default=None)
    parent_id: int | None = Field(default=None)
    password_hash: str | None = Field(default=None)
