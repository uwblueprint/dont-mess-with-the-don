import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.enum import StrikeReasonEnum
from app.models.event import Event
from app.models.registration import Registration
from app.models.strike import Strike
from app.services.implementations.check_in_service import toronto_now


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
