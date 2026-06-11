from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import Enum
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel
from .enum import RegistrationStatusEnum


class RegistrationBase(SQLModel):
    """Shared fields between table and API models for Registration"""

    user_id: int = Field(foreign_key="users.id")
    event_instance_id: UUID = Field(foreign_key="events.id")
    status: RegistrationStatusEnum = Field(
        default=RegistrationStatusEnum.WAITLIST,
        sa_column=Column(
            Enum(
                RegistrationStatusEnum,
                values_callable=lambda obj: [e.value for e in obj],
                name="registrationstatusenum",
            )
        ),
    )
    registered_at: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("America/Toronto")).replace(tzinfo=None),
    )
    response_id: int | None = Field(default=None, foreign_key="form_submissions.id")


class Registration(RegistrationBase, BaseModel, table=True):
    """Registration model"""

    __tablename__ = "registrations"

    id: int | None = Field(default=None, primary_key=True)


class RegistrationCreate(RegistrationBase):
    """Registration creation request"""

    pass


class RegistrationRead(RegistrationBase):
    """Registration response model"""

    id: int
    updated_at: datetime | None = None
    created_at: datetime | None = None


class RegistrationUpdate(SQLModel):
    """Registration update request - all fields optional"""

    user_id: int | None = Field(default=None)
    event_instance_id: UUID | None = Field(default=None)
    status: RegistrationStatusEnum | None = None
    response_id: int | None = Field(default=None)
