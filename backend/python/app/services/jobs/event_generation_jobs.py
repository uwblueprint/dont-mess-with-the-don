"""Generate dated events from active recurring event series."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from sqlmodel import select

from app import models
from app.config import settings
from app.dependencies.services import get_logger
from app.models.event import Event
from app.models.event_series import EventSeries


def _local_now() -> datetime:
    """Return the scheduler's local time as the naive datetime stored by the app."""
    return datetime.now(ZoneInfo(settings.scheduler_timezone)).replace(tzinfo=None)


def _series_start(series: EventSeries, fallback: datetime) -> datetime:
    """Use the series creation date as the RRULE anchor and its configured start time."""
    anchor = series.created_at or fallback
    return datetime.combine(anchor.date(), series.start_time)


def occurrence_datetimes(
    series: EventSeries, window_start: datetime, window_end: datetime
) -> list[datetime]:
    """Expand a series' RRULE into occurrence starts within the requested window."""
    rule = rrulestr(series.recurrence, dtstart=_series_start(series, window_start))
    return list(rule.between(window_start, window_end, inc=True))


def _event_from_series(series: EventSeries, start_datetime: datetime) -> Event:
    """Create one dated event from the fields shared by an event series."""
    end_datetime = datetime.combine(start_datetime.date(), series.end_time)
    if end_datetime <= start_datetime:
        end_datetime += timedelta(days=1)

    return Event(
        name=series.name,
        description=series.description,
        location=series.location,
        max_attendees=series.max_attendees,
        event_status=series.event_status,
        event_type_id=series.event_type_id,
        image=series.image,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        image_urls=series.image_urls,
        notes=series.notes,
        event_series_id=series.id,
    )


async def generate_recurring_events(now: datetime | None = None) -> int:
    """Create missing event instances through the configured rolling horizon.

    ``event_series.recurrence`` is an RFC 5545 RRULE.  A series is anchored to
    its creation date and configured start time; the rule's occurrences are then
    generated from the current time through the configured horizon.  Existing
    ``(event_series_id, start_datetime)`` pairs are skipped, so this is safe to
    run repeatedly.
    """
    logger = get_logger()
    if models.async_session_maker_instance is None:
        logger.error("Database session maker not initialized")
        return 0

    window_start = now or _local_now()
    window_end = window_start + timedelta(days=settings.event_generation_horizon_days)
    created_count = 0

    try:
        async with models.async_session_maker_instance() as session:
            result = await session.execute(
                select(EventSeries).where(EventSeries.is_active.is_(True))
            )
            series_list = result.scalars().all()

            for series in series_list:
                try:
                    starts = occurrence_datetimes(series, window_start, window_end)
                except (TypeError, ValueError) as error:
                    logger.error(
                        "Skipping event series %s because its recurrence is invalid: %s",
                        series.id,
                        error,
                    )
                    continue

                existing_result = await session.execute(
                    select(Event.start_datetime).where(
                        Event.event_series_id == series.id,
                        Event.start_datetime >= window_start,
                        Event.start_datetime <= window_end,
                    )
                )
                existing_starts = set(existing_result.scalars().all())

                for start_datetime in starts:
                    if start_datetime in existing_starts:
                        continue
                    session.add(_event_from_series(series, start_datetime))
                    created_count += 1

            await session.commit()
    except Exception as error:
        logger.error("Failed to generate recurring events: %s", error, exc_info=True)
        raise

    logger.info("Generated %d recurring event instances", created_count)
    return created_count
