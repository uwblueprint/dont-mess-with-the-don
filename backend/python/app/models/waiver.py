from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from .base import BaseModel


class WaiverBase(SQLModel):
    """Shared fields between table and API models for Waiver"""

    event_type: UUID | None = Field(default=None, foreign_key="event_types.id")
    document_url: str = Field(min_length=1)


class Waiver(WaiverBase, BaseModel, table=True):
    """Waiver table model"""

    __tablename__ = "waivers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class WaiverCreate(WaiverBase):
    """Waiver creation request"""

    pass


class WaiverRead(WaiverBase):
    """Waiver response model"""

    id: UUID


class WaiverUpdate(SQLModel):
    """Waiver update request - all fields optional"""

    event_type: UUID | None = Field(default=None)
    document_url: str | None = Field(default=None, min_length=1)
