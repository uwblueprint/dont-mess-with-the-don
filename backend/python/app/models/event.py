from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, String
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel


class EventBase(SQLModel):
    """Shared fields between table and API models"""

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=255)
    max_attendees: int = Field(ge=0)
    event_status: str = Field(min_length=1, max_length=255)
    image: str = Field(min_length=1)
    start_time: datetime
    end_time: datetime
    image_urls: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    notes: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))


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
    event_type: UUID | None = Field(default=None)
    event_status: str | None = Field(default=None, min_length=1, max_length=255)
    image: str | None = Field(default=None, min_length=1)
    start_time: datetime | None = Field(default=None)
    end_time: datetime | None = Field(default=None)
    image_urls: list[str] | None = Field(default=None)
    notes: list[str] | None = Field(default=None)
