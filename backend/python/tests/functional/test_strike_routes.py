from datetime import datetime, timedelta

import pytest
from dateutil.relativedelta import relativedelta

from app.config import settings
from app.dependencies.auth import get_current_user
from app.models.enum import UserRole
from app.models.user import User
from app.services.implementations.check_in_service import toronto_now

# Every test starts logged in as the conftest's fake admin (id 0); `act_as` switches user.


@pytest.fixture(autouse=True)
def _six_month_expiry(monkeypatch):
    monkeypatch.setattr(settings, "strike_expiry_months", 6)


async def create_user(client, **fields) -> dict:
    response = await client.post("/users/", json=fields)
    assert response.status_code == 201, response.text
    return response.json()


async def create_event(client, start: datetime) -> dict:
    response = await client.post(
        "/events",
        json={
            "name": "Hockey Night",
            "description": "Strike test event",
            "location": "Toronto",
            "max_attendees": 20,
            "event_status": "published",
            "headline_image_key": "event-images/event.jpg",
            "start_datetime": start.isoformat(),
            "end_datetime": (start + timedelta(hours=2)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def give_strike(client, user_id: int, note: str = "Left early", **fields) -> dict:
    response = await client.post("/strikes", json={"user_id": user_id, "note": note, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def act_as(app, user: dict, role: UserRole = UserRole.ATTENDEE) -> None:
    caller = User(id=user["id"], email=user.get("email"), role=role)
    app.dependency_overrides[get_current_user] = lambda: caller


# --- POST /strikes ---


async def test_admin_gives_a_manual_strike_for_an_event(client):
    user = await create_user(client, email="manual@example.com")
    start = datetime(2026, 12, 15, 10, 0)
    event = await create_event(client, start)

    response = await client.post(
        "/strikes", json={"user_id": user["id"], "event_id": event["id"], "note": "Was rude"}
    )

    assert response.status_code == 201
    strike = response.json()
    assert strike["user_id"] == user["id"]
    assert strike["event_id"] == event["id"]
    assert strike["registration_id"] is None
    assert strike["reason"] == "manual"
    assert strike["note"] == "Was rude"
    assert strike["issued_by"] == 0
    assert strike["active"] is True
    assert datetime.fromisoformat(strike["expires_at"]) == datetime(2027, 6, 15, 10, 0)


async def test_manual_strike_without_event_expires_six_months_after_creation(client):
    user = await create_user(client, email="no_event@example.com")
    before = toronto_now()

    strike = await give_strike(client, user["id"])

    created_at = datetime.fromisoformat(strike["created_at"])
    assert before <= created_at <= toronto_now()
    assert datetime.fromisoformat(strike["expires_at"]) == created_at + relativedelta(months=6)


@pytest.mark.parametrize("body", [{"note": ""}, {}], ids=["empty-note", "no-note"])
async def test_manual_strike_requires_a_note(client, body):
    user = await create_user(client, email="note@example.com")

    response = await client.post("/strikes", json={"user_id": user["id"], **body})

    assert response.status_code == 422


async def test_manual_strike_for_unknown_user_returns_400(client):
    response = await client.post("/strikes", json={"user_id": 999_999, "note": "Who?"})

    assert response.status_code == 400


async def test_manual_strike_for_unknown_event_returns_400(client):
    user = await create_user(client, email="ghost_event@example.com")

    response = await client.post(
        "/strikes",
        json={
            "user_id": user["id"],
            "event_id": "00000000-0000-0000-0000-000000000000",
            "note": "x",
        },
    )

    assert response.status_code == 400


async def test_attendee_cannot_give_strikes(app, client):
    user = await create_user(client, email="attendee@example.com")
    act_as(app, user)

    response = await client.post("/strikes", json={"user_id": user["id"], "note": "Self strike"})

    assert response.status_code == 403


async def test_giving_strikes_requires_login(app, client):
    app.dependency_overrides.pop(get_current_user)

    response = await client.post("/strikes", json={"user_id": 1, "note": "x"})

    assert response.status_code == 401
