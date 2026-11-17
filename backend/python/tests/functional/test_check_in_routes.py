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
            "headline_image_key": "event-images/event.jpg",
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


# --- POST /events/{id}/check-in ---


async def check_in(client, event_id: str, token: str, user_ids: list[int] | None = None):
    body: dict = {"token": token}
    if user_ids is not None:
        body["user_ids"] = user_ids
    return await client.post(f"/events/{event_id}/check-in", json=body)


def results(response) -> list[tuple[int, str]]:
    return [(r["user_id"], r["result"]) for r in response.json()["results"]]


async def attendance_rows(app, client, admin_override, event_id: str) -> list[dict]:
    caller_override = app.dependency_overrides[get_current_user]
    app.dependency_overrides[get_current_user] = admin_override
    response = await client.get("/attendance/", params={"event_instance_id": event_id})
    app.dependency_overrides[get_current_user] = caller_override
    return response.json()


@pytest.fixture
def admin_override(app):
    """The conftest's fake-admin login, to switch back to after act_as."""
    return app.dependency_overrides[get_current_user]


async def test_post_check_in_wrong_token_returns_403(client, open_event):
    event_id, _ = open_event

    response = await check_in(client, event_id, "wrong")

    assert response.status_code == 403


async def test_post_check_in_unknown_event_returns_404(client):
    response = await check_in(client, str(uuid4()), "any")

    assert response.status_code == 404


async def test_post_check_in_requires_login(app, client, open_event):
    event_id, token = open_event
    app.dependency_overrides.pop(get_current_user)

    response = await check_in(client, event_id, token)

    assert response.status_code == 401


async def test_post_check_in_16_minutes_before_start_returns_409_opens_at(app, client):
    event_id, token = await create_event(client, toronto_now() + timedelta(minutes=16))
    user = await create_user(client, email="too_early@example.com")
    await register(client, user["id"], event_id)
    act_as(app, user)

    response = await check_in(client, event_id, token)

    assert response.status_code == 409
    assert "opens at" in response.json()["detail"]


async def test_post_check_in_14_minutes_before_start_checks_in(app, client):
    event_id, token = await create_event(client, toronto_now() + timedelta(minutes=14))
    user = await create_user(client, email="on_time@example.com")
    await register(client, user["id"], event_id)
    act_as(app, user)

    response = await check_in(client, event_id, token)

    assert response.status_code == 200
    assert results(response) == [(user["id"], "checked_in")]


async def test_post_check_in_after_end_returns_409_closed(app, client):
    start = toronto_now() - timedelta(hours=3)
    event_id, token = await create_event(client, start, end=start + timedelta(hours=2))
    user = await create_user(client, email="too_late@example.com")
    await register(client, user["id"], event_id)
    act_as(app, user)

    response = await check_in(client, event_id, token)

    assert response.status_code == 409
    assert "closed" in response.json()["detail"]


async def test_post_check_in_without_user_ids_checks_in_caller(
    app, client, open_event, admin_override
):
    event_id, token = open_event
    user = await create_user(client, email="self@example.com")
    await register(client, user["id"], event_id)
    act_as(app, user)

    response = await check_in(client, event_id, token)

    assert results(response) == [(user["id"], "checked_in")]
    rows = await attendance_rows(app, client, admin_override, event_id)
    assert [row["user_id"] for row in rows] == [user["id"]]
    assert rows[0]["attended_at"] is not None


@pytest.mark.parametrize(
    ("registration_status", "expected"),
    [(None, "not_registered"), ("waitlist", "waitlisted"), ("cancelled", "cancelled")],
)
async def test_post_check_in_without_accepted_registration(
    app, client, open_event, admin_override, registration_status, expected
):
    event_id, token = open_event
    user = await create_user(client, email="not_accepted@example.com")
    if registration_status is not None:
        await register(client, user["id"], event_id, registration_status)
    act_as(app, user)

    response = await check_in(client, event_id, token)

    assert response.status_code == 200
    assert results(response) == [(user["id"], expected)]
    assert await attendance_rows(app, client, admin_override, event_id) == []


async def test_guardian_checks_in_two_children_at_once(app, client, open_event, admin_override):
    event_id, token = open_event
    parent = await create_user(client, email="guardian@example.com")
    first_child = await create_user(client, profile_type="child", guardian_id=parent["id"])
    second_child = await create_user(client, profile_type="child", guardian_id=parent["id"])
    await register(client, first_child["id"], event_id)
    await register(client, second_child["id"], event_id)
    act_as(app, parent)

    response = await check_in(client, event_id, token, [first_child["id"], second_child["id"]])

    assert response.status_code == 200
    assert results(response) == [
        (first_child["id"], "checked_in"),
        (second_child["id"], "checked_in"),
    ]
    rows = await attendance_rows(app, client, admin_override, event_id)
    assert sorted(row["user_id"] for row in rows) == sorted([first_child["id"], second_child["id"]])


async def test_checking_in_someone_who_is_not_your_child_returns_403(
    app, client, open_event, admin_override
):
    event_id, token = open_event
    parent = await create_user(client, email="parent2@example.com")
    child = await create_user(client, profile_type="child", guardian_id=parent["id"])
    stranger = await create_user(client, email="not_my_kid@example.com")
    await register(client, child["id"], event_id)
    await register(client, stranger["id"], event_id)
    act_as(app, parent)

    response = await check_in(client, event_id, token, [child["id"], stranger["id"]])

    assert response.status_code == 403
    # Nobody is checked in, not even the parent's own child
    assert await attendance_rows(app, client, admin_override, event_id) == []


async def test_admin_checks_in_someone_else(client, open_event):
    event_id, token = open_event
    attendee = await create_user(client, email="walk_in@example.com")
    await register(client, attendee["id"], event_id)

    response = await check_in(client, event_id, token, [attendee["id"]])

    assert response.status_code == 200
    assert results(response) == [(attendee["id"], "checked_in")]


async def test_empty_user_ids_returns_400(app, client, open_event):
    event_id, token = open_event
    user = await create_user(client, email="empty@example.com")
    act_as(app, user)

    response = await check_in(client, event_id, token, [])

    assert response.status_code == 400


async def test_duplicate_user_ids_check_in_once(app, client, open_event, admin_override):
    event_id, token = open_event
    user = await create_user(client, email="dupe@example.com")
    await register(client, user["id"], event_id)
    act_as(app, user)

    response = await check_in(client, event_id, token, [user["id"], user["id"]])

    assert results(response) == [(user["id"], "checked_in")]
    assert len(await attendance_rows(app, client, admin_override, event_id)) == 1


async def test_scanning_twice_returns_already_checked_in(app, client, open_event):
    event_id, token = open_event
    user = await create_user(client, email="twice@example.com")
    await register(client, user["id"], event_id)
    act_as(app, user)

    first = await check_in(client, event_id, token)
    second = await check_in(client, event_id, token)

    assert results(first) == [(user["id"], "checked_in")]
    assert second.status_code == 200
    assert results(second) == [(user["id"], "already_checked_in")]


async def test_existing_row_without_attended_at_gets_checked_in(
    app, client, open_event, admin_override
):
    event_id, token = open_event
    user = await create_user(client, email="pre_made_row@example.com")
    await register(client, user["id"], event_id)
    row = await client.post(
        "/attendance/", json={"user_id": user["id"], "event_instance_id": event_id}
    )
    assert row.status_code == 201
    assert row.json()["attended_at"] is None
    act_as(app, user)

    response = await check_in(client, event_id, token)

    assert results(response) == [(user["id"], "checked_in")]
    rows = await attendance_rows(app, client, admin_override, event_id)
    assert len(rows) == 1
    assert rows[0]["attended_at"] is not None
