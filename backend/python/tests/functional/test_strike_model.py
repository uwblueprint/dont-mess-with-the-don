from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models.enum import StrikeReasonEnum
from app.models.strike import Strike

EXPIRES = datetime(2027, 6, 1, 10)


@pytest.fixture
async def user_and_registration(make_user, make_event, make_registration):
    user = await make_user()
    event = await make_event(start=datetime(2026, 12, 1, 10))
    return user, await make_registration(user, event)


async def test_strike_round_trips_with_defaults(db_session, make_strike, user_and_registration):
    user, registration = user_and_registration
    await make_strike(user, EXPIRES, reason=StrikeReasonEnum.NO_SHOW, registration=registration)
    await db_session.commit()

    strike = (await db_session.execute(select(Strike))).scalars().one()

    assert strike.reason == StrikeReasonEnum.NO_SHOW
    assert strike.issued_by is None
    assert strike.revoked_at is None
    assert strike.created_at is not None


async def test_duplicate_strike_for_same_registration_is_rejected(
    db_session, make_strike, user_and_registration
):
    user, registration = user_and_registration
    await make_strike(user, EXPIRES, registration=registration)
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await make_strike(user, EXPIRES, registration=registration)


async def test_strikes_without_a_registration_are_not_unique(db_session, make_user, make_strike):
    user = await make_user()
    await make_strike(user, EXPIRES, note="first")
    await make_strike(user, EXPIRES, note="second")

    await db_session.commit()
