from uuid import UUID

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel


class FormSubmissionBase(SQLModel):
    """Shared fields between table and API models for FormSubmission"""

    user_id: int = Field(foreign_key="users.id")
    event_instance_id: UUID = Field(foreign_key="events.id")
    response_json: dict | None = Field(default=None, sa_column=Column(JSONB))


class FormSubmission(FormSubmissionBase, BaseModel, table=True):
    """FormSubmission table model"""

    __tablename__ = "form_submissions"

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
