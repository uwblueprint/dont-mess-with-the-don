import logging
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import exists, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.config import settings
from app.models.attendance import Attendance
from app.models.enum import RegistrationStatusEnum, StrikeReasonEnum
from app.models.event import Event
from app.models.registration import Registration
from app.models.strike import Strike
from app.services.implementations.check_in_service import toronto_now

# People with this many active strikes must confirm before each event (the 72-hour rule)
STRIKES_REQUIRING_CONFIRMATION = 2


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
