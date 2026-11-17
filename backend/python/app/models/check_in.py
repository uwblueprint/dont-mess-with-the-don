from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlmodel import SQLModel


class CheckInWindowState(str, Enum):
    NOT_OPEN = "not_open"
    OPEN = "open"
    CLOSED = "closed"


class CheckInRegistrationStatus(str, Enum):
    ACCEPTED = "accepted"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"
    NOT_REGISTERED = "not_registered"


class CheckInResult(str, Enum):
    CHECKED_IN = "checked_in"
    ALREADY_CHECKED_IN = "already_checked_in"
    NOT_REGISTERED = "not_registered"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"


class CheckInWindow(SQLModel):
    """When check-in is open for an event: from opens_at until closes_at (the event end)"""

    state: CheckInWindowState
    opens_at: datetime
    closes_at: datetime


class CheckInEventRead(SQLModel):
    id: UUID
    name: str
    start_datetime: datetime
    end_datetime: datetime


class CheckInPersonRead(SQLModel):
    """Someone the caller can check in: themselves or one of their children"""

    user_id: int
    first_name: str | None
    last_name: str | None
    is_self: bool
    registration_status: CheckInRegistrationStatus
    checked_in: bool


class CheckInStatusRead(SQLModel):
    event: CheckInEventRead
    window: CheckInWindow
    people: list[CheckInPersonRead]


class CheckInRequest(SQLModel):
    token: str
    # Who to check in. Left out means the caller.
    user_ids: list[int] | None = None


class CheckInPersonResult(SQLModel):
    user_id: int
    result: CheckInResult


class CheckInResponse(SQLModel):
    results: list[CheckInPersonResult]
