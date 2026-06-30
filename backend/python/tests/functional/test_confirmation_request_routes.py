import uuid

BASE = "/confirmation_requests/"
USERS_BASE = "/users/"
REGISTRATIONS_BASE = "/registrations/"


async def _create_registration(client, email: str, event_id: str | None = None) -> dict:
    """Helper: create a user and registration, return registration data."""
    user_resp = await client.post(USERS_BASE, json={"email": email})
    assert user_resp.status_code == 201
    user_id = user_resp.json()["id"]

    event_id = event_id or str(uuid.uuid4())
    reg_resp = await client.post(
        REGISTRATIONS_BASE,
        json={"user_id": user_id, "event_instance_id": event_id, "status": "waitlist"},
    )
    assert reg_resp.status_code == 201
    return reg_resp.json()


def _confirmation_payload(registration_id: int, **overrides) -> dict:
    return {
        "registration_id": registration_id,
        "email_status": "pending",
        "timestamp": "2026-01-01T00:00:00",
        "deadline": "2026-01-07T00:00:00",
        **overrides,
    }


async def test_create_confirmation_request_returns_201(client):
    reg = await _create_registration(client, "cr_create@example.com")
    response = await client.post(BASE, json=_confirmation_payload(reg["id"]))
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["registration_id"] == reg["id"]
    assert data["email_status"] == "pending"
    assert data["confirmation_time"] is None


async def test_get_confirmation_requests_returns_200(client):
    reg = await _create_registration(client, "cr_list@example.com")
    await client.post(BASE, json=_confirmation_payload(reg["id"]))

    response = await client.get(BASE)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


async def test_get_confirmation_request_by_id_returns_200(client):
    reg = await _create_registration(client, "cr_fetch@example.com")
    create_resp = await client.post(BASE, json=_confirmation_payload(reg["id"]))
    request_id = create_resp.json()["id"]

    response = await client.get(f"{BASE}{request_id}")
    assert response.status_code == 200
    assert response.json()["id"] == request_id


async def test_get_nonexistent_confirmation_request_returns_404(client):
    response = await client.get(f"{BASE}{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_confirmation_requests_by_event_returns_matching_records(client):
    event_id = str(uuid.uuid4())
    other_event_id = str(uuid.uuid4())

    # Two registrations for the target event, one for a different event
    reg1 = await _create_registration(client, "cr_event1@example.com", event_id)
    reg2 = await _create_registration(client, "cr_event2@example.com", event_id)
    reg_other = await _create_registration(client, "cr_other@example.com", other_event_id)

    await client.post(BASE, json=_confirmation_payload(reg1["id"]))
    await client.post(BASE, json=_confirmation_payload(reg2["id"]))
    await client.post(BASE, json=_confirmation_payload(reg_other["id"]))

    response = await client.get(f"{BASE}event/{event_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    returned_reg_ids = {r["registration_id"] for r in data}
    assert returned_reg_ids == {reg1["id"], reg2["id"]}


async def test_get_confirmation_requests_by_event_returns_empty_for_unknown_event(client):
    response = await client.get(f"{BASE}event/{uuid.uuid4()}")
    assert response.status_code == 200
    assert response.json() == []


async def test_update_confirmation_request_returns_200(client):
    reg = await _create_registration(client, "cr_update@example.com")
    create_resp = await client.post(BASE, json=_confirmation_payload(reg["id"]))
    request_id = create_resp.json()["id"]

    response = await client.patch(
        f"{BASE}{request_id}",
        json={"email_status": "sent", "confirmation_time": "2026-01-03T12:00:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email_status"] == "sent"
    assert data["confirmation_time"] == "2026-01-03T12:00:00"
    assert data["id"] == request_id


async def test_update_confirmation_request_partial_update_leaves_other_fields_unchanged(client):
    reg = await _create_registration(client, "cr_partial@example.com")
    create_resp = await client.post(BASE, json=_confirmation_payload(reg["id"]))
    request_id = create_resp.json()["id"]

    response = await client.patch(f"{BASE}{request_id}", json={"email_status": "failed"})
    assert response.status_code == 200
    data = response.json()
    assert data["email_status"] == "failed"
    assert data["deadline"] == "2026-01-07T00:00:00"


async def test_update_nonexistent_confirmation_request_returns_404(client):
    response = await client.patch(f"{BASE}{uuid.uuid4()}", json={"email_status": "sent"})
    assert response.status_code == 404


async def test_delete_confirmation_request_returns_204(client):
    reg = await _create_registration(client, "cr_delete@example.com")
    create_resp = await client.post(BASE, json=_confirmation_payload(reg["id"]))
    request_id = create_resp.json()["id"]

    response = await client.delete(f"{BASE}{request_id}")
    assert response.status_code == 204

    get_resp = await client.get(f"{BASE}{request_id}")
    assert get_resp.status_code == 404


async def test_delete_nonexistent_confirmation_request_returns_404(client):
    response = await client.delete(f"{BASE}{uuid.uuid4()}")
    assert response.status_code == 404
