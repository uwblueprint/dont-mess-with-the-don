from datetime import datetime, time
from uuid import UUID, uuid4

from dateutil.rrule import rrulestr
from pydantic import field_validator
from sqlalchemy import ARRAY, Enum, String
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel
from .enum import EventRegistrationTypeEnum

# Rules the recurring-event job can expand safely (see validate_recurrence)
ALLOWED_FREQUENCIES = {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}
TIME_OF_DAY_PARTS = {"BYHOUR", "BYMINUTE", "BYSECOND"}


class EventSeriesBase(SQLModel):
    """Shared fields between table and API models"""

    recurrence: str = Field(
        min_length=1,
        max_length=255,
        description="An RFC 5545 RRULE, for example FREQ=WEEKLY;BYDAY=SA",
    )
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

    @field_validator("recurrence")
    @classmethod
    def validate_recurrence(cls, value: str) -> str:
        """Require one RFC 5545 RRULE that the event job can expand safely.

        Only DAILY, WEEKLY, MONTHLY or YEARLY with INTERVAL >= 1: shorter frequencies
        create thousands of events, and INTERVAL=0 never finishes expanding. DTSTART
        and BYHOUR/BYMINUTE/BYSECOND aren't allowed because the job anchors each
        series at its own created_at date and start_time.
        """
        try:
            rrulestr(value, dtstart=datetime(2000, 1, 1))
        # IndexError: dateutil raises it for a DTSTART line with no RRULE
        except (TypeError, ValueError, IndexError) as error:
            raise ValueError("must be a valid RFC 5545 RRULE") from error

        rule = value.strip().upper().removeprefix("RRULE:")
        if any(char.isspace() for char in rule):
            raise ValueError("must be a single RRULE line, without DTSTART")
        parts = dict(part.split("=", 1) for part in rule.split(";") if "=" in part)
        if parts.get("FREQ") not in ALLOWED_FREQUENCIES:
            raise ValueError("FREQ must be DAILY, WEEKLY, MONTHLY or YEARLY")
        if int(parts.get("INTERVAL", "1")) < 1:
            raise ValueError("INTERVAL must be at least 1")
        if TIME_OF_DAY_PARTS & parts.keys():
            raise ValueError(
                "BYHOUR, BYMINUTE and BYSECOND aren't allowed; start_time sets the time"
            )
        return value


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

    @field_validator("recurrence")
    @classmethod
    def validate_recurrence(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return EventSeriesBase.validate_recurrence(value)
