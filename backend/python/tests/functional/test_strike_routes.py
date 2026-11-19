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


# --- GET /strikes ---


async def test_admin_lists_strikes_with_filters(client):
    first = await create_user(client, email="first@example.com")
    second = await create_user(client, email="second@example.com")
    event = await create_event(client, datetime(2026, 12, 15, 10, 0))
    for_event = await give_strike(client, first["id"], event_id=event["id"])
    no_event = await give_strike(client, first["id"])
    other_user = await give_strike(client, second["id"], event_id=event["id"])

    everything = await client.get("/strikes")
    by_user = await client.get("/strikes", params={"user_id": first["id"]})
    by_event = await client.get("/strikes", params={"event_id": event["id"]})
    both = await client.get("/strikes", params={"user_id": first["id"], "event_id": event["id"]})

    def ids(response) -> set[str]:
        assert response.status_code == 200
        return {strike["id"] for strike in response.json()}

    assert ids(everything) == {for_event["id"], no_event["id"], other_user["id"]}
    assert ids(by_user) == {for_event["id"], no_event["id"]}
    assert ids(by_event) == {for_event["id"], other_user["id"]}
    assert ids(both) == {for_event["id"]}


async def test_attendee_cannot_list_strikes(app, client):
    user = await create_user(client, email="nosy@example.com")
    act_as(app, user)

    response = await client.get("/strikes", params={"user_id": user["id"]})

    assert response.status_code == 403


async def test_listing_strikes_requires_login(app, client):
    app.dependency_overrides.pop(get_current_user)

    assert (await client.get("/strikes")).status_code == 401


# --- POST /strikes/{id}/revoke ---


async def test_admin_revokes_a_strike(client):
    user = await create_user(client, email="forgiven@example.com")
    strike = await give_strike(client, user["id"])
    before = toronto_now()

    response = await client.post(
        f"/strikes/{strike['id']}/revoke", json={"reason": "Had a doctor's note"}
    )

    assert response.status_code == 200
    revoked = response.json()
    assert revoked["active"] is False
    assert revoked["revoked_by"] == 0
    assert revoked["revoke_reason"] == "Had a doctor's note"
    assert before <= datetime.fromisoformat(revoked["revoked_at"]) <= toronto_now()


@pytest.mark.parametrize("body", [{"reason": ""}, {}], ids=["empty-reason", "no-reason"])
async def test_revoking_requires_a_reason(client, body):
    user = await create_user(client, email="reasonless@example.com")
    strike = await give_strike(client, user["id"])

    response = await client.post(f"/strikes/{strike['id']}/revoke", json=body)

    assert response.status_code == 422


async def test_revoking_an_unknown_strike_returns_404(client):
    response = await client.post(
        "/strikes/00000000-0000-0000-0000-000000000000/revoke", json={"reason": "x"}
    )

    assert response.status_code == 404


async def test_revoking_twice_returns_409(client):
    user = await create_user(client, email="twice_revoked@example.com")
    strike = await give_strike(client, user["id"])
    await client.post(f"/strikes/{strike['id']}/revoke", json={"reason": "first"})

    response = await client.post(f"/strikes/{strike['id']}/revoke", json={"reason": "second"})

    assert response.status_code == 409


async def test_attendee_cannot_revoke_strikes(app, client):
    user = await create_user(client, email="self_forgiver@example.com")
    strike = await give_strike(client, user["id"])
    act_as(app, user)

    response = await client.post(f"/strikes/{strike['id']}/revoke", json={"reason": "please"})

    assert response.status_code == 403


async def test_revoking_requires_login(app, client):
    app.dependency_overrides.pop(get_current_user)

    response = await client.post(
        "/strikes/00000000-0000-0000-0000-000000000000/revoke", json={"reason": "x"}
    )

    assert response.status_code == 401


# --- GET /users/me/strikes ---


async def test_my_strikes_include_my_children_labelled_by_name(app, client):
    parent = await create_user(client, email="mine@example.com", first_name="Pat", last_name="Lee")
    child = await create_user(
        client, profile_type="child", guardian_id=parent["id"], first_name="Kim", last_name="Lee"
    )
    stranger = await create_user(client, email="not_mine@example.com", first_name="Sam")
    own = await give_strike(client, parent["id"], note="Missed cleanup")
    childs = await give_strike(client, child["id"], note="Missed hockey")
    await give_strike(client, stranger["id"], note="Not visible to Pat")
    await client.post(f"/strikes/{own['id']}/revoke", json={"reason": "Excused"})
    act_as(app, parent)

    response = await client.get("/users/me/strikes")

    assert response.status_code == 200
    strikes = {s["id"]: s for s in response.json()}
    assert set(strikes) == {own["id"], childs["id"]}
    assert (strikes[own["id"]]["first_name"], strikes[own["id"]]["last_name"]) == ("Pat", "Lee")
    assert strikes[own["id"]]["active"] is False
    assert (strikes[childs["id"]]["first_name"], strikes[childs["id"]]["user_id"]) == (
        "Kim",
        child["id"],
    )
    assert strikes[childs["id"]]["active"] is True


async def test_my_strikes_are_empty_without_any(app, client):
    user = await create_user(client, email="clean@example.com")
    act_as(app, user)

    response = await client.get("/users/me/strikes")

    assert response.status_code == 200
    assert response.json() == []


async def test_my_strikes_for_an_admin_are_only_their_own(app, client):
    admin = await create_user(client, email="admin_user@example.com")
    other = await create_user(client, email="someone@example.com")
    await give_strike(client, other["id"])
    act_as(app, admin, role=UserRole.ADMIN)

    response = await client.get("/users/me/strikes")

    assert response.json() == []


async def test_my_strikes_requires_login(app, client):
    app.dependency_overrides.pop(get_current_user)

    assert (await client.get("/users/me/strikes")).status_code == 401
