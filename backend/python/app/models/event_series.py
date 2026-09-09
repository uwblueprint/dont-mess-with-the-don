from datetime import datetime, time
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, Enum, String
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel
from .enum import EventRegistrationTypeEnum


class EventSeriesBase(SQLModel):
    """Shared fields between table and API models"""

    recurrence: str = Field(min_length=1, max_length=255)
    is_active: bool = Field(default=True)
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=255)
    max_attendees: int = Field(ge=0)
    max_waitlist: int = Field(ge=0)
    event_type_id: UUID | None = Field(default=None, foreign_key="event_types.id")
    event_status: str = Field(min_length=1, max_length=255)
    image: str = Field(min_length=1)
    start_time: time
    end_time: time
    image_urls: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    notes: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    registration_type: EventRegistrationTypeEnum = Field(
        sa_column=Column(
            Enum(
                EventRegistrationTypeEnum,
                values_callable=lambda obj: [e.value for e in obj],
                name="eventregistrationtypeenum",
            ),
            nullable=False,
        ),
    )


class EventSeries(EventSeriesBase, BaseModel, table=True):
    """EventSeries model"""

    __tablename__ = "event_series"

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class EventSeriesCreate(EventSeriesBase):
    """EventSeries creation request"""

    pass


class EventSeriesRead(EventSeriesBase):
    """EventSeries response model"""

    id: UUID
    created_at: datetime | None
    updated_at: datetime | None


class EventSeriesUpdate(SQLModel):
    """EventSeries update request - all fields optional"""

    recurrence: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = Field(default=None)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    max_attendees: int | None = Field(default=None, ge=0)
    max_waitlist: int | None = Field(default=None, ge=0)
    event_type_id: UUID | None = Field(default=None, foreign_key="event_types.id")
    event_status: str | None = Field(default=None, min_length=1, max_length=255)
    image: str | None = Field(default=None, min_length=1)
    start_time: time | None = Field(default=None)
    end_time: time | None = Field(default=None)
    image_urls: list[str] | None = Field(default=None)
    notes: list[str] | None = Field(default=None)
    registration_type: EventRegistrationTypeEnum | None = Field(default=None)
