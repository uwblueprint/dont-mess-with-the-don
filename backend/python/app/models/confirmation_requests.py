from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from .base import BaseModel


class ConfirmationRequestBase(SQLModel):
    registration_id: int = Field(foreign_key="registrations.id")
    email_status: str = Field(max_length=255)
    timestamp: datetime
    confirmation_time: datetime | None = Field(default=None)
    deadline: datetime


class ConfirmationRequest(ConfirmationRequestBase, BaseModel, table=True):
    __tablename__ = "confirmation_requests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class ConfirmationRequestCreate(ConfirmationRequestBase):
    pass


class ConfirmationRequestRead(ConfirmationRequestBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConfirmationRequestUpdate(SQLModel):
    registration_id: int | None = Field(default=None)
    email_status: str | None = Field(default=None, max_length=255)
    timestamp: datetime | None = Field(default=None)
    confirmation_time: datetime | None = Field(default=None)
    deadline: datetime | None = Field(default=None)
