from urllib.parse import urlparse
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel


class EventTypeBase(SQLModel):
    """Shared fields between table and API models"""

    name: str = Field(min_length=1, max_length=255)
    image: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=255)
    max_attendees: int = Field(ge=0)
    cancellation_cutoff_hours: int = Field(default=48, ge=0)
    form_json: dict = Field(default_factory=dict, sa_column=Column(JSONB))

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: str) -> str:
        return validate_image_url(v)


class EventType(EventTypeBase, BaseModel, table=True):
    """EventType model"""

    __tablename__ = "event_types"
    __table_args__ = (UniqueConstraint("name", name="uq_event_types_name"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class EventTypeCreate(EventTypeBase):
    """EventType creation request"""

    pass


class EventTypeRead(EventTypeBase):
    """EventType response model"""

    id: UUID


class EventTypeUpdate(SQLModel):
    """EventType update request - all fields optional"""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    image: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    max_attendees: int | None = Field(default=None, ge=0)
    cancellation_cutoff_hours: int | None = Field(default=None, ge=0)
    form_json: dict | None = Field(default=None)

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_image_url(v)


def validate_image_url(v: str) -> str:
    """Ensure the image is a valid HTTP or HTTPS URL"""
    parsed = urlparse(v)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("must be a valid HTTP or HTTPS URL")
    return v
