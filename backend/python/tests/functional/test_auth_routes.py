import uuid
from datetime import date, timedelta

import pytest
from firebase_admin import auth as firebase_auth

from app.dependencies import auth
from app.dependencies.auth import get_current_user, get_token_claims

REGISTER_BODY = {
    "first_name": "Sam",
    "last_name": "Lee",
    "date_of_birth": "2000-01-01",
    "phone_number": "416-555-0199",
}


@pytest.fixture
def log_in_as(app):
    """Act as a Firebase account (skipping the real token check) instead of the fake admin.

    Returns a function that switches back to the fake admin.
    """
    fake_admin = app.dependency_overrides[get_current_user]

    def _log_in(uid="uid-sam", email="sam@example.com"):
        app.dependency_overrides.pop(get_current_user)
        app.dependency_overrides[get_token_claims] = lambda: {"uid": uid, "email": email}

        def back_to_admin():
            app.dependency_overrides[get_current_user] = fake_admin

        return back_to_admin

    return _log_in


async def test_missing_token_returns_401(app, client):
    app.dependency_overrides.pop(get_current_user)
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_invalid_token_returns_401(app, client, monkeypatch):
    def reject(*args, **kwargs):
        raise firebase_auth.InvalidIdTokenError("bad token")

    monkeypatch.setattr(auth.firebase_auth, "verify_id_token", reject)
    monkeypatch.setattr(auth, "get_firebase_app", lambda: None)
    app.dependency_overrides.pop(get_current_user)

    response = await client.get("/users/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


async def test_valid_token_without_profile_returns_403(client, log_in_as):
    log_in_as()
    response = await client.get("/users/me")
    assert response.status_code == 403


async def test_register_creates_attendee_profile(client, log_in_as):
    log_in_as(email="sam@example.com")
    # role in the body is ignored: nobody can make themselves an admin
    response = await client.post("/auth/register", json={**REGISTER_BODY, "role": "admin"})
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "sam@example.com"
    assert data["role"] == "attendee"

    me = await client.get("/users/me")
    assert me.status_code == 200
    assert me.json()["id"] == data["id"]


async def test_register_twice_returns_409(client, log_in_as):
    log_in_as()
    await client.post("/auth/register", json=REGISTER_BODY)
    response = await client.post("/auth/register", json=REGISTER_BODY)
    assert response.status_code == 409


async def test_register_with_used_email_returns_409(client, log_in_as):
    await client.post("/users/", json={"email": "taken@example.com"})
    log_in_as(email="taken@example.com")
    response = await client.post("/auth/register", json=REGISTER_BODY)
    assert response.status_code == 409


async def test_register_with_used_phone_returns_409(client, log_in_as):
    await client.post(
        "/users/", json={"email": "other@example.com", "phone_number": "416-555-0199"}
    )
    log_in_as()
    response = await client.post("/auth/register", json=REGISTER_BODY)
    assert response.status_code == 409


async def test_register_under_16_returns_422(client, log_in_as):
    log_in_as()
    fifteen_years_ago = (date.today() - timedelta(days=15 * 365)).isoformat()
    response = await client.post(
        "/auth/register", json={**REGISTER_BODY, "date_of_birth": fifteen_years_ago}
    )
    assert response.status_code == 422


async def test_update_me_only_changes_allowed_fields(client, log_in_as):
    log_in_as()
    await client.post("/auth/register", json=REGISTER_BODY)
    response = await client.patch(
        "/users/me", json={"first_name": "Samantha", "role": "admin", "guardian_id": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Samantha"
    assert data["role"] == "attendee"
    assert data["guardian_id"] is None


async def test_attendee_gets_403_on_admin_routes(client, log_in_as):
    log_in_as()
    await client.post("/auth/register", json=REGISTER_BODY)
    assert (await client.get("/users/")).status_code == 403
    assert (await client.get("/registrations/")).status_code == 403
    assert (await client.post("/event-types/", json={"name": "Kayaking"})).status_code == 403


async def test_event_browsing_needs_no_login(app, client):
    app.dependency_overrides.pop(get_current_user)
    assert (await client.get("/events")).status_code == 200
    assert (await client.get("/event-types/")).status_code == 200
    assert (await client.get("/event-series/")).status_code == 200


async def test_attendee_can_register_self_and_child_but_not_others(client, log_in_as):
    stranger = await client.post("/users/", json={"email": "stranger@example.com"})
    back_to_admin = log_in_as()
    me = await client.post("/auth/register", json=REGISTER_BODY)
    my_id = me.json()["id"]
    back_to_admin()
    child = await client.post("/users/", json={"profile_type": "child", "guardian_id": my_id})
    log_in_as()

    def registration_for(user_id):
        return {"user_id": user_id, "event_instance_id": str(uuid.uuid4())}

    assert (await client.post("/registrations/", json=registration_for(my_id))).status_code == 201
    child_registration = registration_for(child.json()["id"])
    assert (await client.post("/registrations/", json=child_registration)).status_code == 201
    stranger_registration = registration_for(stranger.json()["id"])
    assert (await client.post("/registrations/", json=stranger_registration)).status_code == 403
    stranger_submission = {**stranger_registration, "response_json": {}}
    assert (await client.post("/form_submissions/", json=stranger_submission)).status_code == 403
