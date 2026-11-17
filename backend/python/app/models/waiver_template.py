from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import event
from sqlmodel import Field, SQLModel

from .base import BaseModel
from .object_key import ObjectKey


class WaiverTemplateBase(SQLModel):
    """Shared fields between table and API models for a blank waiver template (public-read).

    Templates are a library. Each event points at the template its attendees sign
    (events.waiver_template_id), copied from the event type or series default when
    the event is created; only the event's own value applies afterwards.
    """

    document_key: ObjectKey = Field(min_length=1)


class WaiverTemplate(WaiverTemplateBase, BaseModel, table=True):
    """Waiver template table model.

    Templates cannot be edited once created: signed waivers point at a template, so
    changing it would change what people agreed to. To change a waiver, create a new
    template.
    """

    __tablename__ = "waiver_template"

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class WaiverTemplateCreate(WaiverTemplateBase):
    """Waiver template creation request"""

    pass


class WaiverTemplateRead(WaiverTemplateBase):
    """Waiver template response model (key hidden; public `document_url` exposed)"""

    document_key: str = Field(exclude=True)
    document_url: str
    id: UUID


@event.listens_for(WaiverTemplate, "before_update")
def _reject_template_update(_mapper: Any, _connection: Any, _target: WaiverTemplate) -> None:
    raise ValueError("Waiver templates cannot be edited; create a new template instead")
