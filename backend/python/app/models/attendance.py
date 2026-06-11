from datetime import datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from .base import BaseModel

class AttendanceBase(SQLModel):
    user_id: int = Field(foreign_key="users.id")
    event_id: UUID = Field(foreign_key="events.id")
    attended_at: datetime | None = None

class Attendance(AttendanceBase, BaseModel, table=True):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("user_id", "event_id"),)
    id: int | None = Field(default=None, primary_key=True)

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceRead(AttendanceBase):
    id: int