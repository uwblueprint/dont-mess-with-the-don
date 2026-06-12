from uuid import UUID, uuid4

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


class EventType(EventTypeBase, BaseModel, table=True):
    """EventType model"""

    __tablename__ = "event_types"

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
