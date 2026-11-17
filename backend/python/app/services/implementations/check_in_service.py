import logging
import secrets
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.config import settings
from app.models.attendance import Attendance
from app.models.check_in import (
    CheckInEventRead,
    CheckInPersonRead,
    CheckInRegistrationStatus,
    CheckInStatusRead,
    CheckInWindow,
    CheckInWindowState,
)
from app.models.enum import RegistrationStatusEnum
from app.models.event import Event
from app.models.registration import Registration
from app.models.user import User

_REGISTRATION_STATUS = {
    RegistrationStatusEnum.ACCEPTED: CheckInRegistrationStatus.ACCEPTED,
    RegistrationStatusEnum.WAITLIST: CheckInRegistrationStatus.WAITLISTED,
    RegistrationStatusEnum.CANCELLED: CheckInRegistrationStatus.CANCELLED,
}


class EventNotFoundError(LookupError):
    """The event being checked into does not exist."""


class InvalidCheckInTokenError(Exception):
    """The check-in token does not match the event's."""


def toronto_now() -> datetime:
    """Current Toronto time, naive, matching how the app stores datetimes."""
    return datetime.now(ZoneInfo("America/Toronto")).replace(tzinfo=None)


class CheckInService:
    """Event check-in: token verification, the check-in window, and checking people in"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_event_for_check_in(
        self, session: AsyncSession, event_id: UUID, token: str
    ) -> Event:
        """Return the event if it exists and the token matches its check-in token."""
        event = await session.get(Event, event_id)
        if event is None:
            raise EventNotFoundError(f"Event with id {event_id} not found")
        # Compare bytes so a non-ASCII token is a mismatch rather than a TypeError
        if not secrets.compare_digest(token.encode(), event.check_in_token.encode()):
            raise InvalidCheckInTokenError("Invalid check-in token")
        return event

    def get_window(self, event: Event, now: datetime) -> CheckInWindow:
        """Check-in opens a set number of minutes before the start and closes at the end."""
        opens_at = event.start_datetime - timedelta(minutes=settings.check_in_opens_minutes_before)
        closes_at = event.end_datetime
        if now < opens_at:
            state = CheckInWindowState.NOT_OPEN
        elif now > closes_at:
            state = CheckInWindowState.CLOSED
        else:
            state = CheckInWindowState.OPEN
        return CheckInWindow(state=state, opens_at=opens_at, closes_at=closes_at)

    async def get_registration_status(
        self, session: AsyncSession, user_id: int, event_id: UUID
    ) -> CheckInRegistrationStatus:
        """Status of the user's most recent registration for the event."""
        # Registrations aren't unique per (user, event), so the latest one is current
        statement = (
            select(Registration)
            .where(
                Registration.user_id == user_id,
                Registration.event_instance_id == event_id,
            )
            .order_by(col(Registration.registered_at).desc(), col(Registration.id).desc())
            .limit(1)
        )
        result = await session.execute(statement)
        registration = result.scalars().first()
        if registration is None:
            return CheckInRegistrationStatus.NOT_REGISTERED
        return _REGISTRATION_STATUS[RegistrationStatusEnum(registration.status)]

    async def get_attendance(
        self, session: AsyncSession, user_id: int, event_id: UUID
    ) -> Attendance | None:
        statement = select(Attendance).where(
            Attendance.user_id == user_id,
            Attendance.event_instance_id == event_id,
        )
        result = await session.execute(statement)
        return result.scalars().first()

    async def get_check_in_status(
        self, session: AsyncSession, event: Event, caller: User, now: datetime
    ) -> CheckInStatusRead:
        """The event, its check-in window, and the caller and their children."""
        children_result = await session.execute(
            select(User).where(User.guardian_id == caller.id).order_by(col(User.id))
        )
        people = []
        for person in [caller, *children_result.scalars().all()]:
            if person.id is None:  # only unsaved users lack an id
                continue
            attendance = await self.get_attendance(session, person.id, event.id)
            people.append(
                CheckInPersonRead(
                    user_id=person.id,
                    first_name=person.first_name,
                    last_name=person.last_name,
                    is_self=person.id == caller.id,
                    registration_status=await self.get_registration_status(
                        session, person.id, event.id
                    ),
                    checked_in=attendance is not None and attendance.attended_at is not None,
                )
            )
        return CheckInStatusRead(
            event=CheckInEventRead.model_validate(event, from_attributes=True),
            window=self.get_window(event, now),
            people=people,
        )
