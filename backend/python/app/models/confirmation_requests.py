from datetime import datetime
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlalchemy import Enum, UniqueConstraint
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel
from .enum import ConfirmationRequestStatusEnum


class ConfirmationRequestBase(SQLModel):
    registration_id: int = Field(foreign_key="registrations.id")
    email_status: ConfirmationRequestStatusEnum = Field(
        sa_column=Column(
            Enum(
                ConfirmationRequestStatusEnum,
                values_callable=lambda obj: [e.value for e in obj],
                name="confirmationrequeststatusenum",
            ),
            nullable=False,
        )
    )
    confirmation_time: datetime | None = Field(default=None)
    deadline: datetime


class ConfirmationRequest(ConfirmationRequestBase, BaseModel, table=True):
    __tablename__ = "confirmation_requests"
    __table_args__ = (
        UniqueConstraint("registration_id", name="uq_confirmation_requests_registration_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class ConfirmationRequestCreate(ConfirmationRequestBase):
    pass


class ConfirmationRequestRead(ConfirmationRequestBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConfirmationRequestUpdate(SQLModel):
    email_status: ConfirmationRequestStatusEnum | None = None
    confirmation_time: datetime | None = Field(default=None)
    deadline: datetime | None = Field(default=None)

    @field_validator("email_status", "deadline", mode="before")
    @classmethod
    def reject_null_required_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null")
        return value
