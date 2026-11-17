from datetime import datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from .base import BaseModel
from .object_key import ObjectKey


class WaiverSignedBase(SQLModel):
    """Shared fields for a completed/signed waiver (private bucket, signed URLs only).

    Signed waivers are legal records, so every foreign key is RESTRICT: a user, event or
    template that a signed waiver points at cannot be deleted.
    """

    user_id: int = Field(foreign_key="users.id", ondelete="RESTRICT", index=True)
    signed_by_user_id: int = Field(foreign_key="users.id", ondelete="RESTRICT")
    event_id: UUID = Field(foreign_key="events.id", ondelete="RESTRICT", index=True)
    waiver_template_id: UUID = Field(foreign_key="waiver_template.id", ondelete="RESTRICT")
    document_key: ObjectKey = Field(min_length=1)
    signed_at: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("America/Toronto")).replace(tzinfo=None),
    )


class WaiverSigned(WaiverSignedBase, BaseModel, table=True):
    """Signed waiver table model"""

    __tablename__ = "waiver_signed"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_id",
            "waiver_template_id",
            name="uq_waiver_signed_user_event_template",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class WaiverSignedCreate(WaiverSignedBase):
    """Signed waiver creation (internal; created after upload)"""

    pass


class WaiverSignedUrl(SQLModel):
    """Short-lived signed URL response"""

    url: str
    expires_in: int
