from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Enum, Text, UniqueConstraint
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel
from .enum import StrikeReasonEnum


class StrikeBase(SQLModel):
    # The person who missed the event. For a child, that's the child, not the guardian.
    user_id: int = Field(foreign_key="users.id", index=True)
    # Manual strikes may not be tied to an event or a registration
    event_id: UUID | None = Field(default=None, foreign_key="events.id")
    registration_id: int | None = Field(default=None, foreign_key="registrations.id")
    reason: StrikeReasonEnum = Field(
        sa_column=Column(
            Enum(
                StrikeReasonEnum,
                values_callable=lambda obj: [e.value for e in obj],
                name="strikereason",
            ),
            nullable=False,
        )
    )
    note: str | None = Field(default=None, sa_type=Text)
    # Null when the system gave the strike
    issued_by: int | None = Field(default=None, foreign_key="users.id")
    expires_at: datetime
    revoked_at: datetime | None = Field(default=None)
    revoked_by: int | None = Field(default=None, foreign_key="users.id")
    revoke_reason: str | None = Field(default=None, sa_type=Text)


class Strike(StrikeBase, BaseModel, table=True):
    __tablename__ = "strikes"
    # Each registration can get at most one strike
    __table_args__ = (UniqueConstraint("registration_id", name="strikes_registration_id_key"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class StrikeRead(StrikeBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Not revoked and not expired
    active: bool


class StrikeWithUserRead(StrikeRead):
    """A strike labelled with the name of the person it belongs to"""

    first_name: str | None
    last_name: str | None


class StrikeCreate(SQLModel):
    """A manual strike, given by an admin"""

    user_id: int
    event_id: UUID | None = None
    note: str = Field(min_length=1)


class StrikeRevoke(SQLModel):
    reason: str = Field(min_length=1)
