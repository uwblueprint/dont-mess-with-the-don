from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.models import register_models
from app.models.enum import RegistrationStatusEnum, StrikeReasonEnum
from app.models.event import Event
from app.models.registration import Registration
from app.models.strike import Strike
from app.models.user import User


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    register_models()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


async def _registration(session: AsyncSession) -> Registration:
    user = User(email="striker@example.com")
    event = Event(
        name="Cleanup",
        description="d",
        location="Toronto",
        max_attendees=10,
        event_status="published",
        headline_image_key="event-images/cleanup.jpg",
        start_datetime=datetime(2026, 12, 1, 10),
        end_datetime=datetime(2026, 12, 1, 12),
    )
    session.add_all([user, event])
    await session.flush()
    assert user.id is not None
    registration = Registration(
        user_id=user.id, event_instance_id=event.id, status=RegistrationStatusEnum.ACCEPTED
    )
    session.add(registration)
    await session.flush()
    return registration


def _strike(registration: Registration | None, user_id: int, **fields) -> Strike:
    return Strike(
        user_id=user_id,
        event_id=registration.event_instance_id if registration else None,
        registration_id=registration.id if registration else None,
        reason=StrikeReasonEnum.NO_SHOW if registration else StrikeReasonEnum.MANUAL,
        expires_at=datetime(2027, 6, 1, 10),
        **fields,
    )


async def test_strike_round_trips_with_defaults(session):
    registration = await _registration(session)
    session.add(_strike(registration, registration.user_id))
    await session.commit()

    strike = (await session.execute(Strike.__table__.select())).one()

    assert strike.reason == StrikeReasonEnum.NO_SHOW
    assert strike.issued_by is None
    assert strike.revoked_at is None
    assert strike.created_at is not None


async def test_duplicate_strike_for_same_registration_is_rejected(session):
    registration = await _registration(session)
    session.add(_strike(registration, registration.user_id))
    await session.commit()

    session.add(_strike(registration, registration.user_id))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_strikes_without_a_registration_are_not_unique(session):
    registration = await _registration(session)
    session.add_all(
        [
            _strike(None, registration.user_id, note="first"),
            _strike(None, registration.user_id, note="second"),
        ]
    )

    await session.commit()
