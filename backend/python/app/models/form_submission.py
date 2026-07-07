from uuid import UUID

from pydantic import field_validator
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel
from .form import validate_response_json


class FormSubmissionBase(SQLModel):
    """Shared fields between table and API models for FormSubmission"""

    user_id: int = Field(foreign_key="users.id")
    event_instance_id: UUID = Field(foreign_key="events.id")
    response_json: dict | None = Field(default=None, sa_column=Column(JSONB))

    @field_validator("response_json")
    @classmethod
    def _validate_response_json(cls, value: dict | None) -> dict | None:
        return validate_response_json(value)


class FormSubmission(FormSubmissionBase, BaseModel, table=True):
    """FormSubmission table model"""

    __tablename__ = "form_submissions"
    # A user can only respond once per event; re-submitting edits the existing submission
    __table_args__ = (
        UniqueConstraint("user_id", "event_instance_id", name="uq_form_submissions_user_event"),
    )

    id: int | None = Field(default=None, primary_key=True)


class FormSubmissionCreate(FormSubmissionBase):
    """FormSubmission creation request"""

    pass


class FormSubmissionRead(FormSubmissionBase):
    """FormSubmission response model"""

    id: int


class FormSubmissionUpdate(SQLModel):
    """FormSubmission update request - all fields optional"""

    response_json: dict | None = Field(default=None)

    @field_validator("response_json")
    @classmethod
    def _validate_response_json(cls, value: dict | None) -> dict | None:
        return validate_response_json(value)
