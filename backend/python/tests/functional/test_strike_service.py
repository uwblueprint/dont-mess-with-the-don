import logging
from datetime import datetime

import pytest
from sqlmodel import select

from app.config import settings
from app.models.enum import StrikeReasonEnum
from app.models.strike import Strike
from app.services.implementations.strike_service import StrikeService

NOW = datetime(2026, 12, 1, 9, 0)


@pytest.fixture(autouse=True)
def _six_month_expiry(monkeypatch):
    monkeypatch.setattr(settings, "strike_expiry_months", 6)


@pytest.fixture
def service() -> StrikeService:
    return StrikeService(logging.getLogger("test_strikes"))


async def _strikes(db_session) -> list[Strike]:
    return list((await db_session.execute(select(Strike))).scalars().all())


# --- add_registration_strike ---


async def test_registration_strike_is_for_the_registered_person(
    db_session, service, make_user, make_event, make_registration
):
    user = await make_user()
    event = await make_event(start=datetime(2026, 12, 15, 10))
    registration = await make_registration(user, event)

    strike = await service.add_registration_strike(
        db_session, registration, event, StrikeReasonEnum.NO_SHOW, now=NOW
    )
    await db_session.commit()

    assert strike is not None
    assert (strike.user_id, strike.event_id, strike.registration_id) == (
        user.id,
        event.id,
        registration.id,
    )
    assert strike.reason == StrikeReasonEnum.NO_SHOW
    assert strike.issued_by is None
    assert strike.expires_at == datetime(2027, 6, 15, 10)


async def test_child_strike_goes_to_the_child_not_the_guardian(
    db_session, service, make_user, make_event, make_registration
):
    guardian = await make_user()
    child = await make_user(email=None, profile_type="child", guardian_id=guardian.id)
    event = await make_event(start=datetime(2026, 12, 15, 10))
    registration = await make_registration(child, event)

    strike = await service.add_registration_strike(
        db_session, registration, event, StrikeReasonEnum.NO_SHOW, now=NOW
    )

    assert strike is not None
    assert strike.user_id == child.id


async def test_second_strike_for_same_registration_is_skipped(
    db_session, service, make_user, make_event, make_registration
):
    user = await make_user()
    event = await make_event(start=datetime(2026, 12, 15, 10))
    registration = await make_registration(user, event)
    await service.add_registration_strike(
        db_session, registration, event, StrikeReasonEnum.NO_SHOW, now=NOW
    )
    await db_session.commit()

    second = await service.add_registration_strike(
        db_session, registration, event, StrikeReasonEnum.LATE_CANCELLATION, now=NOW
    )
    await db_session.commit()

    assert second is None
    assert len(await _strikes(db_session)) == 1


# --- count_active_strikes ---


async def test_counts_only_strikes_that_are_not_revoked_or_expired(
    db_session, service, make_user, make_strike
):
    user = await make_user()
    await make_strike(user, expires_at=datetime(2027, 1, 1))  # active
    await make_strike(user, expires_at=datetime(2027, 2, 1))  # active
    await make_strike(user, expires_at=datetime(2027, 1, 1), revoked_at=datetime(2026, 11, 1))
    await make_strike(user, expires_at=datetime(2026, 11, 30))  # expired before NOW
    await db_session.commit()

    assert await service.count_active_strikes(db_session, user.id, now=NOW) == 2


async def test_strike_stops_counting_the_moment_it_expires(
    db_session, service, make_user, make_strike
):
    user = await make_user()
    await make_strike(user, expires_at=NOW)
    await db_session.commit()

    assert await service.count_active_strikes(db_session, user.id, now=NOW) == 0


async def test_siblings_strikes_are_counted_separately(db_session, service, make_user, make_strike):
    guardian = await make_user()
    first_child = await make_user(email=None, profile_type="child", guardian_id=guardian.id)
    second_child = await make_user(email=None, profile_type="child", guardian_id=guardian.id)
    await make_strike(first_child, expires_at=datetime(2027, 1, 1))
    await make_strike(second_child, expires_at=datetime(2027, 1, 1))
    await db_session.commit()

    assert await service.count_active_strikes(db_session, first_child.id, now=NOW) == 1
    assert await service.count_active_strikes(db_session, second_child.id, now=NOW) == 1
    assert await service.count_active_strikes(db_session, guardian.id, now=NOW) == 0


# --- requires_confirmation ---


async def test_requires_confirmation_flips_at_two_active_strikes(
    db_session, service, make_user, make_strike
):
    user = await make_user()
    await make_strike(user, expires_at=datetime(2027, 1, 1))
    await db_session.commit()
    assert await service.requires_confirmation(db_session, user.id, now=NOW) is False

    await make_strike(user, expires_at=datetime(2027, 1, 1))
    await db_session.commit()
    assert await service.requires_confirmation(db_session, user.id, now=NOW) is True


async def test_requires_confirmation_flips_back_when_a_strike_is_revoked(
    db_session, service, make_user, make_strike
):
    user = await make_user()
    await make_strike(user, expires_at=datetime(2027, 1, 1))
    second = await make_strike(user, expires_at=datetime(2027, 1, 1))
    await db_session.commit()
    assert await service.requires_confirmation(db_session, user.id, now=NOW) is True

    second.revoked_at = NOW
    await db_session.commit()
    assert await service.requires_confirmation(db_session, user.id, now=NOW) is False


async def test_requires_confirmation_flips_back_when_a_strike_expires(
    db_session, service, make_user, make_strike
):
    user = await make_user()
    await make_strike(user, expires_at=datetime(2027, 1, 1))
    await make_strike(user, expires_at=datetime(2026, 12, 10))
    await db_session.commit()

    assert await service.requires_confirmation(db_session, user.id, now=NOW) is True
    assert (
        await service.requires_confirmation(db_session, user.id, now=datetime(2026, 12, 10))
        is False
    )
