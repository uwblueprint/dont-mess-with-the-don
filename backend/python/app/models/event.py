from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel


class EventBase(SQLModel):
    """Shared fields between table and API models"""

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=255)
    max_attendees: int = Field(ge=0)
    event_status: str = Field(min_length=1, max_length=255)
    event_type_id: UUID | None = Field(default=None, foreign_key="event_types.id")
    image: str = Field(min_length=1)
    start_datetime: datetime
    end_datetime: datetime
    image_urls: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    notes: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    event_series_id: UUID | None = Field(default=None, foreign_key="event_series.id")
    form_json: dict | None = Field(default=None, sa_column=Column(JSONB))


class Event(EventBase, BaseModel, table=True):
    """Event model"""

    __tablename__ = "events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class EventCreate(EventBase):
    """Event creation request"""

    pass


class EventRead(EventBase):
    """Event response model"""

    id: UUID
    created_at: datetime | None
    updated_at: datetime | None


class EventUpdate(SQLModel):
    """Event update request - all fields optional"""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    max_attendees: int | None = Field(default=None, ge=0)
    event_type_id: UUID | None = Field(default=None, foreign_key="event_types.id")
    event_series_id: UUID | None = Field(default=None, foreign_key="event_series.id")
    event_status: str | None = Field(default=None, min_length=1, max_length=255)
    image: str | None = Field(default=None, min_length=1)
    start_datetime: datetime | None = Field(default=None)
    end_datetime: datetime | None = Field(default=None)
    image_urls: list[str] | None = Field(default=None)
    notes: list[str] | None = Field(default=None)
    recurrence: str | None = Field(default=None, min_length=1, max_length=255)
    form_json: dict | None = Field(default=None)
