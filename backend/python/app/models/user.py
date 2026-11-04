from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from pydantic import EmailStr, field_validator
from sqlalchemy import Column, Index, String, text
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, Relationship, SQLModel

from .base import BaseModel
from .enum import UserProfileType, UserProvider, UserRole

# Younger people are registered by a parent or guardian instead
MIN_SELF_SIGNUP_AGE = 16


class UserBase(SQLModel):
    """Shared fields between table and API models"""

    email: EmailStr | None = Field(default=None, sa_column=Column(String, nullable=True))
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
    first_name: str | None = Field(default=None, min_length=1, max_length=255)
    last_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)
    date_of_birth: datetime | None = Field(default=None)
    gender: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    province: str | None = Field(default=None, max_length=255)
    zip_code: str | None = Field(default=None, max_length=255)

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
            ),
            nullable=False,
        ),
    )
    region: str | None = Field(default=None, max_length=255)
    guardian_id: int | None = Field(default=None, foreign_key="users.id")


class User(UserBase, BaseModel, table=True):
    """User model"""

    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_email_default",
            "email",
            unique=True,
            postgresql_where=text("profile_type = 'default'"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    # Set by POST /auth/register; children and guests don't log in, so theirs stay empty
    firebase_uid: str | None = Field(default=None, max_length=255, unique=True)
    # Never settable through the API; a TL makes someone an admin directly in the database
    role: UserRole = Field(
        default=UserRole.ATTENDEE,
        sa_column=Column(
            SAEnum(
                UserRole,
                values_callable=lambda obj: [e.value for e in obj],
                name="userrole",
                create_type=True,
            ),
            nullable=False,
        ),
    )

    guardian: Optional["User"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "User.id"},
    )
    children: list["User"] = Relationship(back_populates="guardian")


class UserCreate(UserBase):
    """User creation request"""

    pass


class UserRead(UserBase):
    """User response model"""

    id: int
    role: UserRole


class UserUpdate(SQLModel):
    """User update request - all fields optional"""

    email: EmailStr | None = Field(default=None)
    provider: UserProvider | None = Field(default=None)
    profile_pic_url: str | None = Field(default=None, max_length=500)
    profile_type: UserProfileType | None = Field(default=None)
    region: str | None = Field(default=None, max_length=255)
    guardian_id: int | None = Field(default=None)
    first_name: str | None = Field(default=None, min_length=1, max_length=255)
    last_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)
    date_of_birth: datetime | None = Field(default=None)
    gender: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    province: str | None = Field(default=None, max_length=255)
    zip_code: str | None = Field(default=None, max_length=255)


class UserRegister(SQLModel):
    """Sign-up request for POST /auth/register. Email and firebase_uid come from the token"""

    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    date_of_birth: datetime
    phone_number: str | None = Field(default=None, max_length=255)
    gender: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    province: str | None = Field(default=None, max_length=255)
    zip_code: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=255)

    @field_validator("date_of_birth")
    @classmethod
    def validate_old_enough(cls, v: datetime) -> datetime:
        today = datetime.now(ZoneInfo("America/Toronto")).date()
        born = v.date()
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        if age < MIN_SELF_SIGNUP_AGE:
            raise ValueError(
                f"must be {MIN_SELF_SIGNUP_AGE} or older to sign up; "
                "a parent or guardian has to register you"
            )
        return v


class UserSelfUpdate(SQLModel):
    """PATCH /users/me request: the fields people can change on their own profile"""

    first_name: str | None = Field(default=None, min_length=1, max_length=255)
    last_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, max_length=255)
    date_of_birth: datetime | None = Field(default=None)
    gender: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    province: str | None = Field(default=None, max_length=255)
    zip_code: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=255)
