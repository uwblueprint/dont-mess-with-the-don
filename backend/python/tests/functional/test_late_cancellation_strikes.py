import logging
from datetime import datetime, timedelta

import pytest
from sqlmodel import select

from app.config import settings
from app.models.enum import RegistrationStatusEnum, StrikeReasonEnum
from app.models.registration import RegistrationUpdate
from app.models.strike import Strike
from app.services.implementations import registration_service as registration_module
from app.services.implementations.registration_service import RegistrationService

NOW = datetime(2026, 12, 1, 9, 0)
CANCELLED = RegistrationUpdate(status=RegistrationStatusEnum.CANCELLED)


@pytest.fixture(autouse=True)
def _fixed_clock_and_settings(monkeypatch):
    monkeypatch.setattr(registration_module, "toronto_now", lambda: NOW)
    monkeypatch.setattr(settings, "strike_late_cancellation_hours", 48)
    monkeypatch.setattr(settings, "strike_expiry_months", 6)


@pytest.fixture
def service() -> RegistrationService:
    return RegistrationService(logging.getLogger("test_late_cancellation"))


@pytest.fixture
def accepted_registration(make_user, make_event, make_registration):
    async def _make(hours_before_start: float):
        user = await make_user()
        event = await make_event(start=NOW + timedelta(hours=hours_before_start))
        return await make_registration(user, event)

    return _make


async def _strikes(db_session) -> list[Strike]:
    return list((await db_session.execute(select(Strike))).scalars().all())


async def test_cancelling_less_than_48_hours_before_gives_a_strike(
    db_session, service, accepted_registration
):
    registration = await accepted_registration(hours_before_start=47)
    await db_session.commit()

    updated = await service.update_registration(db_session, registration.id, CANCELLED)

    assert updated is not None
    assert updated.cancelled_at == NOW
    assert updated.is_late_cancellation is True
    strikes = await _strikes(db_session)
    assert len(strikes) == 1
    assert strikes[0].reason == StrikeReasonEnum.LATE_CANCELLATION
    assert strikes[0].registration_id == registration.id
    assert strikes[0].user_id == registration.user_id
    # Event starts 2026-12-03 08:00, so the strike expires 6 months later
    assert strikes[0].expires_at == datetime(2027, 6, 3, 8, 0)


@pytest.mark.parametrize("hours_before_start", [48, 72, 24 * 14])
async def test_cancelling_48_hours_or_more_before_gives_no_strike(
    db_session, service, accepted_registration, hours_before_start
):
    registration = await accepted_registration(hours_before_start=hours_before_start)
    await db_session.commit()

    updated = await service.update_registration(db_session, registration.id, CANCELLED)

    assert updated is not None
    assert updated.cancelled_at == NOW
    assert updated.is_late_cancellation is False
    assert await _strikes(db_session) == []


async def test_cancellation_uses_supplied_cancelled_at(db_session, service, accepted_registration):
    registration = await accepted_registration(hours_before_start=72)
    await db_session.commit()
    # Recorded as cancelled 30h before the start, even though it's entered 72h before
    cancelled_at = NOW + timedelta(hours=42)

    updated = await service.update_registration(
        db_session,
        registration.id,
        RegistrationUpdate(status=RegistrationStatusEnum.CANCELLED, cancelled_at=cancelled_at),
    )

    assert updated is not None
    assert updated.cancelled_at == cancelled_at
    assert updated.is_late_cancellation is True
    assert len(await _strikes(db_session)) == 1


async def test_other_updates_give_no_strike(db_session, service, accepted_registration):
    registration = await accepted_registration(hours_before_start=1)
    await db_session.commit()

    await service.update_registration(
        db_session, registration.id, RegistrationUpdate(status=RegistrationStatusEnum.ACCEPTED)
    )

    assert await _strikes(db_session) == []
