import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.check_in import CheckInRegistrationStatus, CheckInResult, CheckInWindowState
from app.services.implementations.check_in_service import (
    CheckInService,
    EventNotFoundError,
    InvalidCheckInTokenError,
)

START = datetime(2026, 12, 15, 10, 0, 0)
END = datetime(2026, 12, 15, 12, 0, 0)


def _service() -> CheckInService:
    return CheckInService(logging.getLogger("test_check_in"))


def _event(token: str = "right-token") -> Mock:
    return Mock(id=uuid4(), start_datetime=START, end_datetime=END, check_in_token=token)


@pytest.fixture(autouse=True)
def _fifteen_minute_window(monkeypatch):
    monkeypatch.setattr(settings, "check_in_opens_minutes_before", 15)


# --- window ---


def test_window_not_open_16_minutes_before_start():
    window = _service().get_window(_event(), now=START - timedelta(minutes=16))

    assert window.state == CheckInWindowState.NOT_OPEN
    assert window.opens_at == START - timedelta(minutes=15)
    assert window.closes_at == END


def test_window_open_14_minutes_before_start():
    window = _service().get_window(_event(), now=START - timedelta(minutes=14))

    assert window.state == CheckInWindowState.OPEN


@pytest.mark.parametrize(
    "now",
    [START - timedelta(minutes=15), START, END],
    ids=["exactly-when-it-opens", "at-start", "exactly-at-end"],
)
def test_window_open_at_its_edges(now):
    assert _service().get_window(_event(), now=now).state == CheckInWindowState.OPEN


def test_window_closed_after_end():
    window = _service().get_window(_event(), now=END + timedelta(seconds=1))

    assert window.state == CheckInWindowState.CLOSED


def test_window_uses_configured_minutes(monkeypatch):
    monkeypatch.setattr(settings, "check_in_opens_minutes_before", 30)

    window = _service().get_window(_event(), now=START - timedelta(minutes=20))

    assert window.state == CheckInWindowState.OPEN
    assert window.opens_at == START - timedelta(minutes=30)


# --- token ---


async def test_get_event_for_check_in_returns_event_for_matching_token():
    event = _event("right-token")
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = event

    assert await _service().get_event_for_check_in(session, event.id, "right-token") is event


@pytest.mark.parametrize("token", ["wrong-token", "", "right-token ", "rïght-token"])
async def test_get_event_for_check_in_rejects_wrong_token(token):
    event = _event("right-token")
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = event

    with pytest.raises(InvalidCheckInTokenError):
        await _service().get_event_for_check_in(session, event.id, token)


async def test_get_event_for_check_in_raises_for_unknown_event():
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = None

    with pytest.raises(EventNotFoundError):
        await _service().get_event_for_check_in(session, uuid4(), "any-token")


# --- registration status ---


@pytest.mark.parametrize(
    ("db_status", "expected"),
    [
        ("accepted", CheckInRegistrationStatus.ACCEPTED),
        ("waitlist", CheckInRegistrationStatus.WAITLISTED),
        ("cancelled", CheckInRegistrationStatus.CANCELLED),
        (None, CheckInRegistrationStatus.NOT_REGISTERED),
    ],
)
async def test_get_registration_status_maps_latest_registration(db_status, expected):
    result = Mock()
    result.scalars.return_value.first.return_value = (
        None if db_status is None else Mock(status=db_status)
    )
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = result

    status = await _service().get_registration_status(session, user_id=1, event_id=uuid4())

    assert status == expected


# --- concurrent scans ---


async def test_check_in_person_returns_already_checked_in_when_a_concurrent_scan_wins():
    accepted = Mock()
    accepted.scalars.return_value.first.return_value = Mock(status="accepted")
    no_row_yet = Mock()
    no_row_yet.scalars.return_value.first.return_value = None
    row_from_other_scan = Mock()
    row_from_other_scan.scalars.return_value.first.return_value = Mock(attended_at=START)
    session = AsyncMock(spec=AsyncSession)
    session.add = Mock()
    session.execute.side_effect = [accepted, no_row_yet, row_from_other_scan]
    session.commit.side_effect = IntegrityError("insert", {}, Exception("unique violation"))

    result = await _service().check_in_person(session, event_id=uuid4(), user_id=1, now=START)

    assert result == CheckInResult.ALREADY_CHECKED_IN
    session.rollback.assert_awaited_once()


async def test_check_in_person_reraises_other_integrity_errors():
    accepted = Mock()
    accepted.scalars.return_value.first.return_value = Mock(status="accepted")
    no_row = Mock()
    no_row.scalars.return_value.first.return_value = None
    session = AsyncMock(spec=AsyncSession)
    session.add = Mock()
    session.execute.side_effect = [accepted, no_row, no_row]
    session.commit.side_effect = IntegrityError("insert", {}, Exception("foreign key"))

    with pytest.raises(IntegrityError):
        await _service().check_in_person(session, event_id=uuid4(), user_id=1, now=START)

    session.rollback.assert_awaited_once()
