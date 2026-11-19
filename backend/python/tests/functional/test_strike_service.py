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
