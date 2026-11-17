from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest

from app.dependencies.auth import get_current_user
from app.models.enum import UserRole
from app.models.user import User
from app.services.implementations.check_in_service import toronto_now

# Every test starts logged in as the conftest's fake admin; `act_as` switches to another user.


async def create_user(client, **fields) -> dict:
    response = await client.post("/users/", json=fields)
    assert response.status_code == 201, response.text
    return response.json()


async def create_event(client, start: datetime, end: datetime | None = None) -> tuple[str, str]:
    """Create an event and return (event_id, check_in_token)."""
    response = await client.post(
        "/events",
        json={
            "name": "Hockey Night",
            "description": "Check-in test event",
            "location": "Toronto",
            "max_attendees": 20,
            "event_status": "published",
            "image": "https://example.com/event.jpg",
            "start_datetime": start.isoformat(),
            "end_datetime": (end or start + timedelta(hours=2)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    event_id = response.json()["id"]
    link = await client.get(f"/events/{event_id}/check-in-link")
    token = parse_qs(urlparse(link.json()["url"]).query)["token"][0]
    return event_id, token


async def register(client, user_id: int, event_id: str, status: str = "accepted") -> None:
    response = await client.post(
        "/registrations/",
        json={"user_id": user_id, "event_instance_id": event_id, "status": status},
    )
    assert response.status_code == 201, response.text


def act_as(app, user: dict, role: UserRole = UserRole.ATTENDEE) -> None:
    caller = User(
        id=user["id"],
        email=user.get("email"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        role=role,
    )
    app.dependency_overrides[get_current_user] = lambda: caller


@pytest.fixture
async def open_event(client) -> tuple[str, str]:
    """An event whose check-in window is open (starts in 10 minutes)."""
    return await create_event(client, toronto_now() + timedelta(minutes=10))


# --- GET /events/{id}/check-in ---


async def test_get_check_in_wrong_token_returns_403(client, open_event):
    event_id, _ = open_event

    response = await client.get(f"/events/{event_id}/check-in", params={"token": "wrong"})

    assert response.status_code == 403


async def test_get_check_in_unknown_event_returns_404(client):
    response = await client.get(f"/events/{uuid4()}/check-in", params={"token": "any"})

    assert response.status_code == 404


async def test_get_check_in_requires_login(app, client, open_event):
    event_id, token = open_event
    app.dependency_overrides.pop(get_current_user)

    response = await client.get(f"/events/{event_id}/check-in", params={"token": token})

    assert response.status_code == 401


async def test_get_check_in_lists_caller_and_children_with_statuses(app, client, open_event):
    event_id, token = open_event
    parent = await create_user(client, email="parent@example.com", first_name="Pat")
    waitlisted_child = await create_user(
        client, profile_type="child", guardian_id=parent["id"], first_name="Wren"
    )
    cancelled_child = await create_user(
        client, profile_type="child", guardian_id=parent["id"], first_name="Cass"
    )
    unregistered_child = await create_user(
        client, profile_type="child", guardian_id=parent["id"], first_name="Nora"
    )
    stranger = await create_user(client, email="stranger@example.com")
    await register(client, parent["id"], event_id, "accepted")
    await register(client, waitlisted_child["id"], event_id, "waitlist")
    await register(client, cancelled_child["id"], event_id, "cancelled")
    await register(client, stranger["id"], event_id, "accepted")
    act_as(app, parent)

    response = await client.get(f"/events/{event_id}/check-in", params={"token": token})

    assert response.status_code == 200
    data = response.json()
    assert data["event"]["id"] == event_id
    assert data["event"]["name"] == "Hockey Night"
    assert data["window"]["state"] == "open"
    people = [
        (p["user_id"], p["first_name"], p["is_self"], p["registration_status"], p["checked_in"])
        for p in data["people"]
    ]
    assert people == [
        (parent["id"], "Pat", True, "accepted", False),
        (waitlisted_child["id"], "Wren", False, "waitlisted", False),
        (cancelled_child["id"], "Cass", False, "cancelled", False),
        (unregistered_child["id"], "Nora", False, "not_registered", False),
    ]


async def test_get_check_in_shows_when_check_in_opens(app, client):
    start = toronto_now() + timedelta(hours=3)
    event_id, token = await create_event(client, start)
    user = await create_user(client, email="early@example.com")
    act_as(app, user)

    response = await client.get(f"/events/{event_id}/check-in", params={"token": token})

    window = response.json()["window"]
    assert window["state"] == "not_open"
    assert datetime.fromisoformat(window["opens_at"]) == start - timedelta(minutes=15)


async def test_get_check_in_shows_closed_after_event_ends(app, client):
    start = toronto_now() - timedelta(hours=3)
    event_id, token = await create_event(client, start)
    user = await create_user(client, email="late@example.com")
    act_as(app, user)

    response = await client.get(f"/events/{event_id}/check-in", params={"token": token})

    assert response.json()["window"]["state"] == "closed"


async def test_get_check_in_shows_who_is_checked_in(app, client, open_event):
    event_id, token = open_event
    user = await create_user(client, email="checked@example.com")
    await register(client, user["id"], event_id)
    attendance = await client.post(
        "/attendance/",
        json={
            "user_id": user["id"],
            "event_instance_id": event_id,
            "attended_at": toronto_now().isoformat(),
        },
    )
    assert attendance.status_code == 201
    act_as(app, user)

    response = await client.get(f"/events/{event_id}/check-in", params={"token": token})

    assert response.json()["people"][0]["checked_in"] is True
