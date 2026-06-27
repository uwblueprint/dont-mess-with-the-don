from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from .base import BaseModel


class EventSeriesBase(SQLModel):
    """Shared fields between table and API models"""

    recurrence: str = Field(min_length=1, max_length=255)
    is_active: bool = Field(default=True)


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
