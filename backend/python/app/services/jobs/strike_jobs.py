"""Give no-show strikes for events nobody checked in to."""

from datetime import datetime

from app import models
from app.dependencies.services import get_logger, get_strike_service


async def issue_no_show_strikes(now: datetime | None = None) -> int:
    """Give a strike to each accepted registration with no check-in after the grace period."""
    logger = get_logger()

    if models.async_session_maker_instance is None:
        logger.error("Database session maker not initialized")
        return 0

    try:
        async with models.async_session_maker_instance() as session:
            issued = await get_strike_service().issue_no_show_strikes(session, now)
            logger.info(f"Gave {issued} no-show strike(s)")
            return issued
    except Exception as e:
        logger.error(f"Error giving no-show strikes: {e}", exc_info=True)
        raise
