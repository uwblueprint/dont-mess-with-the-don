import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta

from app.config import settings
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
