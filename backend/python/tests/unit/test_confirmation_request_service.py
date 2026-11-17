from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.confirmation_requests import ConfirmationRequest, ConfirmationRequestCreate
from app.models.registration import Registration
from app.services.implementations.confirmation_request_service import (
    ConfirmationRequestAlreadyExistsError,
    ConfirmationRequestService,
    RegistrationNotFoundError,
    calculate_confirmation_deadline,
)


async def test_create_confirmation_request_rejects_unknown_registration():
    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    service = ConfirmationRequestService(Mock())
    data = ConfirmationRequestCreate(
        registration_id=999,
        email_status="pending",
        deadline=datetime(2026, 1, 7),
    )

    with pytest.raises(RegistrationNotFoundError, match="Registration 999 does not exist"):
        await service.create_confirmation_request(session, data)

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_create_confirmation_request_preserves_other_integrity_errors():
    session = AsyncMock(spec=AsyncSession)
    registration = Mock()
    registration.scalar_one_or_none.return_value = 42
    no_request = Mock()
    no_request.scalar_one_or_none.return_value = None
    session.execute.side_effect = [registration, no_request, registration]
    session.commit.side_effect = IntegrityError("statement", {}, Exception("another constraint"))
    service = ConfirmationRequestService(Mock())
    data = ConfirmationRequestCreate(
        registration_id=42,
        email_status="pending",
        deadline=datetime(2026, 1, 7),
    )

    with pytest.raises(IntegrityError):
        await service.create_confirmation_request(session, data)

    session.rollback.assert_awaited_once()


async def test_create_confirmation_request_reports_duplicate_after_integrity_error():
    session = AsyncMock(spec=AsyncSession)
    registration = Mock()
    registration.scalar_one_or_none.return_value = 42
    existing_request = Mock()
    existing_request.scalar_one_or_none.return_value = "request-id"
    session.execute.side_effect = [registration, existing_request]
    session.commit.side_effect = IntegrityError("statement", {}, Exception("unique constraint"))
    service = ConfirmationRequestService(Mock())
    data = ConfirmationRequestCreate(
        registration_id=42,
        email_status="pending",
        deadline=datetime(2026, 1, 7),
    )

    with pytest.raises(
        ConfirmationRequestAlreadyExistsError,
        match="Registration 42 already has a confirmation request",
    ):
        await service.create_confirmation_request(session, data)

    session.rollback.assert_awaited_once()


@pytest.mark.parametrize(
    ("strike_count", "expected"),
    [(1, False), (2, True)],
)
async def test_requires_positive_confirmation_uses_two_strike_threshold(
    strike_count: int, expected: bool
):
    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.scalar_one.return_value = strike_count
    session.execute.return_value = result
    service = ConfirmationRequestService(Mock())

    requires_confirmation = await service.requires_positive_confirmation(
        session,
        user_id=42,
        as_of=datetime(2026, 10, 7),
    )

    assert requires_confirmation is expected
    session.execute.assert_awaited_once()


EVENT_START = datetime(2026, 12, 15, 10, 0, 0)


@pytest.mark.parametrize(
    ("signed_up_before_event", "expected_deadline"),
    [
        # Early signup: the usual deadline, 72h before the event
        (timedelta(days=14), EVENT_START - timedelta(hours=72)),
        # Exactly 96h before: 72h-before and 24h-after-signup are the same moment
        (timedelta(hours=96), EVENT_START - timedelta(hours=72)),
        # 80h before: 72h-before would leave only 8h, so they get 24h after signup
        (timedelta(hours=80), EVENT_START - timedelta(hours=56)),
        # 48h before: 72h-before has already passed, so 24h after signup
        (timedelta(hours=48), EVENT_START - timedelta(hours=24)),
        # Exactly 24h before: 24h after signup is the event start
        (timedelta(hours=24), EVENT_START),
        # 10h before: 24h after signup is past the event, so capped at the event start
        (timedelta(hours=10), EVENT_START),
    ],
)
def test_calculate_confirmation_deadline(
    signed_up_before_event: timedelta, expected_deadline: datetime
):
    deadline = calculate_confirmation_deadline(
        event_start=EVENT_START, signed_up_at=EVENT_START - signed_up_before_event
    )

    assert deadline == expected_deadline


@pytest.mark.parametrize("hours_before_event", [24 * 30, 100, 73, 48, 25, 24, 12, 1])
def test_confirmation_deadline_is_never_passed_or_after_event_start(hours_before_event: int):
    signed_up_at = EVENT_START - timedelta(hours=hours_before_event)

    deadline = calculate_confirmation_deadline(event_start=EVENT_START, signed_up_at=signed_up_at)

    assert signed_up_at < deadline <= EVENT_START


async def test_late_signup_request_uses_deadline_from_signup_time():
    signed_up_at = EVENT_START - timedelta(hours=48)
    registration = Registration(
        id=7,
        user_id=42,
        event_instance_id=uuid4(),
        status="accepted",
        created_at=signed_up_at,
    )
    session = AsyncMock(spec=AsyncSession)
    session.add = Mock()
    session.get.return_value = Mock(start_datetime=EVENT_START)
    service = ConfirmationRequestService(Mock())
    service.requires_positive_confirmation = AsyncMock(return_value=True)  # type: ignore[method-assign]

    await service.add_for_registration_if_required(session, registration)

    session.add.assert_called_once()
    request = session.add.call_args.args[0]
    assert isinstance(request, ConfirmationRequest)
    assert request.registration_id == 7
    assert request.deadline == signed_up_at + timedelta(hours=24)
