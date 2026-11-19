import logging
from datetime import datetime, timedelta
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlalchemy import exists, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.config import settings
from app.models.attendance import Attendance
from app.models.enum import RegistrationStatusEnum, StrikeReasonEnum
from app.models.event import Event
from app.models.registration import Registration
from app.models.strike import Strike, StrikeCreate
from app.models.user import User
from app.services.implementations.check_in_service import toronto_now

# People with this many active strikes must confirm before each event (the 72-hour rule)
STRIKES_REQUIRING_CONFIRMATION = 2


class StrikeTargetNotFoundError(ValueError):
    """The user or event a manual strike refers to does not exist."""


class StrikeNotFoundError(LookupError):
    """The strike does not exist."""


class StrikeAlreadyRevokedError(ValueError):
    """The strike was already revoked."""


def strike_expires_at(event_start: datetime | None, created_at: datetime | None) -> datetime:
    """When a strike expires: a set number of months after the event's start.

    A manual strike with no event expires that long after it was created. Month ends
    clamp (Aug 31 + 6 months is Feb 28).
    """
    base = event_start or created_at or toronto_now()
    return base + relativedelta(months=settings.strike_expiry_months)


class StrikeService:
    """Strikes for missed events: giving, counting, listing and revoking them"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def add_registration_strike(
        self,
        session: AsyncSession,
        registration: Registration,
        event: Event,
        reason: StrikeReasonEnum,
        now: datetime,
    ) -> Strike | None:
        """Stage a system strike for a registration; the caller commits.

        Returns None, without error, if the registration already has a strike.
        """
        existing = await session.execute(
            select(Strike.id).where(Strike.registration_id == registration.id)
        )
        if existing.first() is not None:
            return None

        strike = Strike(
            user_id=registration.user_id,
            event_id=event.id,
            registration_id=registration.id,
            reason=reason,
            created_at=now,
            expires_at=strike_expires_at(event.start_datetime, now),
        )
        session.add(strike)
        return strike

    async def count_active_strikes(
        self, session: AsyncSession, user_id: int, now: datetime | None = None
    ) -> int:
        """Strikes for this one person that aren't revoked and haven't expired."""
        now = now or toronto_now()
        statement = select(func.count(col(Strike.id))).where(
            Strike.user_id == user_id,
            col(Strike.revoked_at).is_(None),
            col(Strike.expires_at) > now,
        )
        result = await session.execute(statement)
        return result.scalar_one()

    async def requires_confirmation(
        self, session: AsyncSession, user_id: int, now: datetime | None = None
    ) -> bool:
        """Whether this person must confirm their spot before events (2+ active strikes)."""
        active = await self.count_active_strikes(session, user_id, now)
        return active >= STRIKES_REQUIRING_CONFIRMATION

    async def issue_no_show_strikes(
        self, session: AsyncSession, now: datetime | None = None
    ) -> int:
        """Give a no-show strike for each accepted registration nobody checked in for.

        Counts events that ended at least the grace period ago, and only those ending at
        or after strike_no_show_start (attendance wasn't recorded before check-in existed).
        Returns how many strikes were given.
        """
        cutoff = settings.strike_no_show_start
        if cutoff is None:
            self.logger.info("strike_no_show_start is unset; not giving no-show strikes")
            return 0
        now = now or toronto_now()
        ended_by = now - timedelta(minutes=settings.strike_no_show_grace_minutes)

        checked_in = exists().where(
            col(Attendance.user_id) == col(Registration.user_id),
            col(Attendance.event_instance_id) == col(Registration.event_instance_id),
            col(Attendance.attended_at).is_not(None),
        )
        has_strike = exists().where(col(Strike.registration_id) == col(Registration.id))
        statement = (
            select(Registration, Event)
            .join(Event, col(Event.id) == col(Registration.event_instance_id))
            .where(
                Registration.status == RegistrationStatusEnum.ACCEPTED,
                Event.event_status != "cancelled",
                col(Event.end_datetime) <= ended_by,
                col(Event.end_datetime) >= cutoff,
                ~checked_in,
                ~has_strike,
            )
        )
        rows = (await session.execute(statement)).all()

        issued = 0
        for registration, event in rows:
            strike = await self.add_registration_strike(
                session, registration, event, StrikeReasonEnum.NO_SHOW, now
            )
            if strike is None:
                continue
            try:
                await session.commit()
                issued += 1
            except IntegrityError:
                # Another run gave this registration a strike first
                await session.rollback()
        return issued

    async def create_manual_strike(
        self, session: AsyncSession, data: StrikeCreate, issued_by: int, now: datetime | None = None
    ) -> Strike:
        """Give a strike by hand. It isn't tied to a registration."""
        now = now or toronto_now()
        if await session.get(User, data.user_id) is None:
            raise StrikeTargetNotFoundError(f"User {data.user_id} does not exist")
        event_start = None
        if data.event_id is not None:
            event = await session.get(Event, data.event_id)
            if event is None:
                raise StrikeTargetNotFoundError(f"Event {data.event_id} does not exist")
            event_start = event.start_datetime

        strike = Strike(
            user_id=data.user_id,
            event_id=data.event_id,
            reason=StrikeReasonEnum.MANUAL,
            note=data.note,
            issued_by=issued_by,
            created_at=now,
            expires_at=strike_expires_at(event_start, now),
        )
        session.add(strike)
        await session.commit()
        await session.refresh(strike)
        return strike

    async def list_strikes(
        self, session: AsyncSession, user_id: int | None = None, event_id: UUID | None = None
    ) -> list[Strike]:
        """All strikes, newest first, optionally for one user and/or one event."""
        statement = select(Strike).order_by(col(Strike.created_at).desc())
        if user_id is not None:
            statement = statement.where(Strike.user_id == user_id)
        if event_id is not None:
            statement = statement.where(Strike.event_id == event_id)
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def revoke_strike(
        self,
        session: AsyncSession,
        strike_id: UUID,
        reason: str,
        revoked_by: int,
        now: datetime | None = None,
    ) -> Strike:
        """Revoke a strike so it no longer counts. A strike can only be revoked once."""
        strike = await session.get(Strike, strike_id)
        if strike is None:
            raise StrikeNotFoundError(f"Strike {strike_id} not found")
        if strike.revoked_at is not None:
            raise StrikeAlreadyRevokedError(f"Strike {strike_id} is already revoked")

        now = now or toronto_now()
        strike.revoked_at = now
        strike.revoked_by = revoked_by
        strike.revoke_reason = reason
        strike.updated_at = now
        await session.commit()
        await session.refresh(strike)
        return strike

    async def list_for_user_and_children(
        self, session: AsyncSession, user: User
    ) -> list[tuple[Strike, User]]:
        """The user's own strikes and their children's, newest first, with whose each is."""
        statement = (
            select(Strike, User)
            .join(User, col(User.id) == col(Strike.user_id))
            .where(or_(col(User.id) == user.id, col(User.guardian_id) == user.id))
            .order_by(col(Strike.created_at).desc())
        )
        result = await session.execute(statement)
        return [(strike, person) for strike, person in result.all()]
