from datetime import datetime, time, timedelta
from typing import Any

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select

from app import models
from app.config import settings
from app.models.enum import EventRegistrationTypeEnum
from app.models.event import Event
from app.models.event_series import EventSeries
from app.models.waiver_template import WaiverTemplate
from app.services.jobs.event_generation_jobs import generate_recurring_events


@pytest_asyncio.fixture
async def job_session_maker(monkeypatch):
    models.register_models()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(models, "async_session_maker_instance", session_maker)
    yield session_maker
    await engine.dispose()


def make_series(**overrides) -> EventSeries:
    values: dict[str, Any] = {
        "recurrence": "FREQ=DAILY",
        "is_active": True,
        "name": "Morning Cleanup",
        "description": "Clean the trail.",
        "location": "Don Valley",
        "max_attendees": 20,
        "max_waitlist": 5,
        "event_status": "published",
        "headline_image_key": "event-images/event.jpg",
        "start_time": time(9),
        "end_time": time(11),
        "registration_type": EventRegistrationTypeEnum.AUTO_APPROVE,
        "created_at": datetime(2026, 1, 1, 12),
    }
    values.update(overrides)
    return EventSeries(**values)


async def test_generates_missing_instances_and_is_idempotent(job_session_maker, monkeypatch):
    monkeypatch.setattr(settings, "event_generation_horizon_days", 2)
    series = make_series()

    async with job_session_maker() as session:
        session.add(series)
        await session.commit()

    now = datetime(2026, 1, 2, 9)
    assert await generate_recurring_events(now) == 3
    assert await generate_recurring_events(now) == 0

    async with job_session_maker() as session:
        events = list(
            (await session.execute(select(Event).order_by(Event.start_datetime))).scalars()
        )

    assert [event.start_datetime for event in events] == [
        datetime(2026, 1, 2, 9),
        datetime(2026, 1, 3, 9),
        datetime(2026, 1, 4, 9),
    ]
    assert all(event.event_series_id == series.id for event in events)
    assert all(event.end_datetime - event.start_datetime == timedelta(hours=2) for event in events)


async def test_ignores_inactive_series(job_session_maker):
    series = make_series(is_active=False)
    async with job_session_maker() as session:
        session.add(series)
        await session.commit()

    assert await generate_recurring_events(datetime(2026, 1, 2, 8)) == 0

    async with job_session_maker() as session:
        assert list((await session.execute(select(Event))).scalars()) == []


async def test_events_copy_the_series_waiver_when_generated(job_session_maker, monkeypatch):
    monkeypatch.setattr(settings, "event_generation_horizon_days", 1)
    old_waiver = WaiverTemplate(document_key="waiver-templates/v1.pdf")
    new_waiver = WaiverTemplate(document_key="waiver-templates/v2.pdf")
    series = make_series(waiver_template_id=old_waiver.id)
    async with job_session_maker() as session:
        session.add_all([old_waiver, new_waiver, series])
        await session.commit()

    assert await generate_recurring_events(datetime(2026, 1, 2, 9)) == 2

    # Changing the series default only affects events generated afterwards
    async with job_session_maker() as session:
        stored = await session.get(EventSeries, series.id)
        assert stored is not None
        stored.waiver_template_id = new_waiver.id
        await session.commit()
    assert await generate_recurring_events(datetime(2026, 1, 3, 9)) == 1

    async with job_session_maker() as session:
        events = list(
            (await session.execute(select(Event).order_by(Event.start_datetime))).scalars()
        )
    assert [event.waiver_template_id for event in events] == [
        old_waiver.id,
        old_waiver.id,
        new_waiver.id,
    ]
