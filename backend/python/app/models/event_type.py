from uuid import UUID, uuid4

from pydantic import field_validator
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel
from .form import validate_form_json
from .object_key import ObjectKey


class EventTypeBase(SQLModel):
    """Shared fields between table and API models"""

    name: str = Field(min_length=1, max_length=255)
    headline_image_key: ObjectKey = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=255)
    max_attendees: int = Field(ge=0)
    cancellation_cutoff_hours: int = Field(default=48, ge=0)
    waiver_template_id: UUID | None = Field(default=None, foreign_key="waiver_template.id")
    form_json: dict = Field(default_factory=dict, sa_column=Column(JSONB))


class EventType(EventTypeBase, BaseModel, table=True):
    """EventType model"""

    __tablename__ = "event_types"
    __table_args__ = (UniqueConstraint("name", name="uq_event_types_name"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class EventTypeCreate(EventTypeBase):
    """EventType creation request"""

    @field_validator("form_json")
    @classmethod
    def _validate_form_json(cls, value: dict) -> dict:
        return validate_form_json(value) or {}


class EventTypeRead(EventTypeBase):
    """EventType response model"""

    headline_image_key: str = Field(exclude=True)  # keys are internal and excluded from output
    headline_image_url: str
    id: UUID


class EventTypeUpdate(SQLModel):
    """EventType update request - all fields optional"""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    headline_image_key: ObjectKey | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    max_attendees: int | None = Field(default=None, ge=0)
    cancellation_cutoff_hours: int | None = Field(default=None, ge=0)
    waiver_template_id: UUID | None = Field(default=None, foreign_key="waiver_template.id")
    form_json: dict | None = Field(default=None)

    @field_validator("form_json")
    @classmethod
    def _validate_form_json(cls, value: dict | None) -> dict | None:
        return validate_form_json(value)
