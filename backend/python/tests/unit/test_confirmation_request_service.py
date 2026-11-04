from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.confirmation_requests import ConfirmationRequestCreate
from app.services.implementations.confirmation_request_service import (
    ConfirmationRequestAlreadyExistsError,
    ConfirmationRequestService,
    RegistrationNotFoundError,
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
