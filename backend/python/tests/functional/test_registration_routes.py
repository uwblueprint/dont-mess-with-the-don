import uuid

BASE = "/registrations/"


async def test_create_registration_returns_201(client):
    # Create a user to get a valid user_id
    user_response = await client.post("/users/", json={"email": "volunteer@example.com"})
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    # We also need a valid event in the database due to foreign key constraints.
    # Since we did metadata.create_all, the tables exist.
    event_id = str(uuid.uuid4())

    reg_payload = {"user_id": user_id, "event_instance_id": event_id, "status": "registered"}

    response = await client.post(BASE, json=reg_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user_id
    assert data["event_instance_id"] == event_id
    assert data["status"] == "registered"
    assert "id" in data


async def test_get_registrations_returns_200(client):
    user_response = await client.post("/users/", json={"email": "volunteer2@example.com"})
    user_id = user_response.json()["id"]
    event_id = str(uuid.uuid4())

    await client.post(
        BASE, json={"user_id": user_id, "event_instance_id": event_id, "status": "registered"}
    )

    response = await client.get(BASE)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


async def test_get_registration_by_id_returns_200(client):
    user_response = await client.post("/users/", json={"email": "volunteer3@example.com"})
    user_id = user_response.json()["id"]
    event_id = str(uuid.uuid4())

    create_resp = await client.post(
        BASE, json={"user_id": user_id, "event_instance_id": event_id, "status": "registered"}
    )
    registration_id = create_resp.json()["id"]

    response = await client.get(f"{BASE}{registration_id}")
    assert response.status_code == 200
    assert response.json()["id"] == registration_id


async def test_get_nonexistent_registration_returns_404(client):
    response = await client.get(f"{BASE}99999")
    assert response.status_code == 404


async def test_update_registration_returns_200(client):
    user_response = await client.post("/users/", json={"email": "volunteer4@example.com"})
    user_id = user_response.json()["id"]
    event_id = str(uuid.uuid4())

    create_resp = await client.post(
        BASE, json={"user_id": user_id, "event_instance_id": event_id, "status": "registered"}
    )
    registration_id = create_resp.json()["id"]

    response = await client.put(
        f"{BASE}{registration_id}", json={"status": "accepted", "is_late_cancellation": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["is_late_cancellation"] is True
    assert data["id"] == registration_id


async def test_update_registration_status_to_cancelled(client):
    user_response = await client.post("/users/", json={"email": "volunteer5@example.com"})
    user_id = user_response.json()["id"]
    event_id = str(uuid.uuid4())

    create_resp = await client.post(
        BASE, json={"user_id": user_id, "event_instance_id": event_id, "status": "registered"}
    )
    registration_id = create_resp.json()["id"]

    response = await client.put(
        f"{BASE}{registration_id}",
        json={"status": "cancelled", "cancelled_at": "2026-06-12T12:00:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_at"] == "2026-06-12T12:00:00"
    assert data["id"] == registration_id


async def test_update_nonexistent_registration_returns_404(client):
    response = await client.put(f"{BASE}99999", json={"status": "accepted"})
    assert response.status_code == 404

