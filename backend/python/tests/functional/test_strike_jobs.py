from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select

from app import models
from app.config import settings
from app.models.enum import RegistrationStatusEnum, StrikeReasonEnum
from app.models.event import Event
from app.models.registration import Registration
from app.models.strike import Strike
from app.models.user import User
from app.services.jobs import init_jobs
from app.services.jobs.strike_jobs import issue_no_show_strikes

NOW = datetime(2026, 12, 1, 20, 0)


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


async def test_job_gives_no_show_strikes(job_session_maker, monkeypatch):
    monkeypatch.setattr(settings, "strike_no_show_start", datetime(2026, 11, 1))
    monkeypatch.setattr(settings, "strike_no_show_grace_minutes", 60)
    async with job_session_maker() as session:
        user = User(email="no_show@example.com")
        event = Event(
            name="Cleanup",
            description="d",
            location="Toronto",
            max_attendees=10,
            event_status="published",
            headline_image_key="event-images/cleanup.jpg",
            start_datetime=NOW - timedelta(hours=4),
            end_datetime=NOW - timedelta(hours=2),
        )
        session.add_all([user, event])
        await session.flush()
        assert user.id is not None
        session.add(
            Registration(
                user_id=user.id,
                event_instance_id=event.id,
                status=RegistrationStatusEnum.ACCEPTED,
            )
        )
        await session.commit()

    assert await issue_no_show_strikes(now=NOW) == 1

    async with job_session_maker() as session:
        strikes = (await session.execute(select(Strike))).scalars().all()
    assert [s.reason for s in strikes] == [StrikeReasonEnum.NO_SHOW]


async def test_job_does_nothing_without_a_database(monkeypatch):
    monkeypatch.setattr(models, "async_session_maker_instance", None)

    assert await issue_no_show_strikes(now=NOW) == 0


def test_job_is_scheduled_every_15_minutes():
    scheduler = Mock()

    init_jobs(scheduler)

    jobs = {call.kwargs["job_id"]: call for call in scheduler.add_cron_job.call_args_list}
    call = jobs["issue_no_show_strikes"]
    assert call.args[0] is issue_no_show_strikes
    assert call.kwargs["minute"] == "*/15"
