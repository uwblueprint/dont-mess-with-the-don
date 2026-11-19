from datetime import datetime

import pytest

from app.config import settings
from app.services.implementations.strike_service import strike_expires_at


@pytest.fixture(autouse=True)
def _six_month_expiry(monkeypatch):
    monkeypatch.setattr(settings, "strike_expiry_months", 6)


def test_expires_six_months_after_event_start():
    expires_at = strike_expires_at(
        event_start=datetime(2026, 12, 15, 10, 0), created_at=datetime(2026, 12, 16, 9, 0)
    )

    assert expires_at == datetime(2027, 6, 15, 10, 0)


def test_manual_strike_without_event_expires_six_months_after_creation():
    expires_at = strike_expires_at(event_start=None, created_at=datetime(2026, 11, 18, 14, 30))

    assert expires_at == datetime(2027, 5, 18, 14, 30)


def test_expiry_clamps_to_end_of_shorter_month():
    expires_at = strike_expires_at(event_start=datetime(2026, 8, 31, 18, 0), created_at=None)

    assert expires_at == datetime(2027, 2, 28, 18, 0)


def test_expiry_uses_configured_months(monkeypatch):
    monkeypatch.setattr(settings, "strike_expiry_months", 3)

    expires_at = strike_expires_at(event_start=datetime(2026, 12, 15, 10, 0), created_at=None)

    assert expires_at == datetime(2027, 3, 15, 10, 0)
