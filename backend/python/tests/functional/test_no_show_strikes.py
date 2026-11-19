import logging
from datetime import datetime, timedelta

import pytest
from sqlmodel import select

from app.config import settings
from app.models.attendance import Attendance
from app.models.enum import RegistrationStatusEnum, StrikeReasonEnum
from app.models.strike import Strike
from app.services.implementations.strike_service import StrikeService

NOW = datetime(2026, 12, 1, 20, 0)
CUTOFF = datetime(2026, 11, 1)


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(settings, "strike_no_show_grace_minutes", 60)
    monkeypatch.setattr(settings, "strike_no_show_start", CUTOFF)
    monkeypatch.setattr(settings, "strike_expiry_months", 6)


@pytest.fixture
def service() -> StrikeService:
    return StrikeService(logging.getLogger("test_no_show"))


@pytest.fixture
def registration_for_event(make_user, make_event, make_registration):
    """An accepted registration for an event that ended `ended_minutes_ago` before NOW."""

    async def _make(
        ended_minutes_ago: int = 61,
        status: RegistrationStatusEnum = RegistrationStatusEnum.ACCEPTED,
        **event_fields,
    ):
        end = NOW - timedelta(minutes=ended_minutes_ago)
        user = await make_user()
        event = await make_event(start=end - timedelta(hours=2), end=end, **event_fields)
        return await make_registration(user, event, status)

    return _make


async def _strikes(db_session) -> list[Strike]:
    return list((await db_session.execute(select(Strike))).scalars().all())


async def test_no_show_strike_after_the_grace_period(db_session, service, registration_for_event):
    registration = await registration_for_event(ended_minutes_ago=61)
    await db_session.commit()

    issued = await service.issue_no_show_strikes(db_session, now=NOW)

    assert issued == 1
    [strike] = await _strikes(db_session)
    assert strike.reason == StrikeReasonEnum.NO_SHOW
    assert (strike.user_id, strike.registration_id) == (registration.user_id, registration.id)
    assert strike.issued_by is None
    # Event started 2026-12-01 16:59, so the strike expires 6 months later
    assert strike.expires_at == datetime(2027, 6, 1, 16, 59)


async def test_no_strike_during_the_grace_period(db_session, service, registration_for_event):
    await registration_for_event(ended_minutes_ago=59)
    await db_session.commit()

    assert await service.issue_no_show_strikes(db_session, now=NOW) == 0
    assert await _strikes(db_session) == []


async def test_no_strike_for_someone_who_checked_in(db_session, service, registration_for_event):
    registration = await registration_for_event()
    db_session.add(
        Attendance(
            user_id=registration.user_id,
            event_instance_id=registration.event_instance_id,
            attended_at=NOW - timedelta(hours=3),
        )
    )
    await db_session.commit()

    assert await service.issue_no_show_strikes(db_session, now=NOW) == 0


async def test_attendance_row_without_attended_at_is_still_a_no_show(
    db_session, service, registration_for_event
):
    registration = await registration_for_event()
    db_session.add(
        Attendance(user_id=registration.user_id, event_instance_id=registration.event_instance_id)
    )
    await db_session.commit()

    assert await service.issue_no_show_strikes(db_session, now=NOW) == 1


@pytest.mark.parametrize(
    "status", [RegistrationStatusEnum.CANCELLED, RegistrationStatusEnum.WAITLIST]
)
async def test_no_strike_for_registrations_that_are_not_accepted(
    db_session, service, registration_for_event, status
):
    await registration_for_event(status=status)
    await db_session.commit()

    assert await service.issue_no_show_strikes(db_session, now=NOW) == 0


async def test_no_strike_when_the_event_was_cancelled(db_session, service, registration_for_event):
    await registration_for_event(event_status="cancelled")
    await db_session.commit()

    assert await service.issue_no_show_strikes(db_session, now=NOW) == 0


async def test_no_strike_for_events_that_ended_before_the_cutoff(
    db_session, service, make_user, make_event, make_registration
):
    user = await make_user()
    event = await make_event(start=CUTOFF - timedelta(hours=3), end=CUTOFF - timedelta(hours=1))
    await make_registration(user, event)
    await db_session.commit()

    assert await service.issue_no_show_strikes(db_session, now=NOW) == 0


async def test_no_strikes_at_all_when_the_cutoff_is_unset(
    db_session, service, registration_for_event, monkeypatch
):
    monkeypatch.setattr(settings, "strike_no_show_start", None)
    await registration_for_event()
    await db_session.commit()

    assert await service.issue_no_show_strikes(db_session, now=NOW) == 0


async def test_running_twice_does_not_duplicate(db_session, service, registration_for_event):
    await registration_for_event()
    await registration_for_event()
    await db_session.commit()

    assert await service.issue_no_show_strikes(db_session, now=NOW) == 2
    assert await service.issue_no_show_strikes(db_session, now=NOW) == 0
    assert len(await _strikes(db_session)) == 2
