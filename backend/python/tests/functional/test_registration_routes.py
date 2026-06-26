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

    reg_payload = {"user_id": user_id, "event_instance_id": event_id, "status": "waitlist"}

    response = await client.post(BASE, json=reg_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user_id
    assert data["event_instance_id"] == event_id
    assert data["status"] == "waitlist"
    assert "id" in data


async def test_get_registrations_returns_200(client):
    user_response = await client.post("/users/", json={"email": "volunteer2@example.com"})
    user_id = user_response.json()["id"]
    event_id = str(uuid.uuid4())

    await client.post(
        BASE, json={"user_id": user_id, "event_instance_id": event_id, "status": "waitlist"}
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
        BASE, json={"user_id": user_id, "event_instance_id": event_id, "status": "waitlist"}
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
        BASE, json={"user_id": user_id, "event_instance_id": event_id, "status": "waitlist"}
    )
    registration_id = create_resp.json()["id"]

    response = await client.patch(
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
        BASE, json={"user_id": user_id, "event_instance_id": event_id, "status": "waitlist"}
    )
    registration_id = create_resp.json()["id"]

    # Waitlist -> Accepted
    accept_resp = await client.patch(f"{BASE}{registration_id}", json={"status": "accepted"})
    assert accept_resp.status_code == 200

    response = await client.patch(
        f"{BASE}{registration_id}",
        json={"status": "cancelled", "cancelled_at": "2026-06-12T12:00:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_at"] == "2026-06-12T12:00:00"
    assert data["id"] == registration_id


async def test_update_nonexistent_registration_returns_404(client):
    response = await client.patch(f"{BASE}99999", json={"status": "accepted"})
    assert response.status_code == 404


async def test_delete_registration_success(client):
    user_response = await client.post("/users/", json={"email": "volunteer_del@example.com"})
    user_id = user_response.json()["id"]
    event_id = str(uuid.uuid4())

    create_resp = await client.post(
        BASE, json={"user_id": user_id, "event_instance_id": event_id, "status": "waitlist"}
    )
    registration_id = create_resp.json()["id"]

    # Delete registration
    del_resp = await client.delete(f"{BASE}{registration_id}")
    assert del_resp.status_code == 204

    # Verify registration is deleted
    get_resp = await client.get(f"{BASE}{registration_id}")
    assert get_resp.status_code == 404


async def test_delete_nonexistent_registration_returns_404(client):
    response = await client.delete(f"{BASE}99999")
    assert response.status_code == 404


async def test_get_registrations_filtering(client):
    user_resp1 = await client.post("/users/", json={"email": "filter1@example.com"})
    user_id1 = user_resp1.json()["id"]
    user_resp2 = await client.post("/users/", json={"email": "filter2@example.com"})
    user_id2 = user_resp2.json()["id"]

    event_id1 = str(uuid.uuid4())
    event_id2 = str(uuid.uuid4())

    # Create registrations
    await client.post(
        BASE, json={"user_id": user_id1, "event_instance_id": event_id1, "status": "waitlist"}
    )
    await client.post(
        BASE, json={"user_id": user_id1, "event_instance_id": event_id2, "status": "accepted"}
    )
    await client.post(
        BASE, json={"user_id": user_id2, "event_instance_id": event_id1, "status": "cancelled"}
    )

    # Filter by user_id
    resp_user = await client.get(f"{BASE}?user_id={user_id1}")
    assert resp_user.status_code == 200
    data = resp_user.json()
    assert len(data) == 2
    assert all(r["user_id"] == user_id1 for r in data)

    # Filter by event_instance_id
    resp_event = await client.get(f"{BASE}?event_instance_id={event_id1}")
    assert resp_event.status_code == 200
    data = resp_event.json()
    assert len(data) == 2
    assert all(r["event_instance_id"] == event_id1 for r in data)

    # Filter by status
    resp_status = await client.get(f"{BASE}?status=waitlist")
    assert resp_status.status_code == 200
    data = resp_status.json()
    assert len(data) == 1
    assert data[0]["status"] == "waitlist"

    # Multiple filters
    resp_multi = await client.get(f"{BASE}?user_id={user_id1}&status=waitlist")
    assert resp_multi.status_code == 200
    data = resp_multi.json()
    assert len(data) == 1
    assert data[0]["user_id"] == user_id1
    assert data[0]["status"] == "waitlist"


async def test_status_transition_constraints(client):
    user_response = await client.post(
        "/users/", json={"email": "volunteer_transitions@example.com"}
    )
    user_id = user_response.json()["id"]
    event_id = str(uuid.uuid4())

    create_resp = await client.post(
        BASE, json={"user_id": user_id, "event_instance_id": event_id, "status": "waitlist"}
    )
    registration_id = create_resp.json()["id"]

    # 1. Waitlist -> Cancelled is prohibited
    resp1 = await client.patch(f"{BASE}{registration_id}", json={"status": "cancelled"})
    assert resp1.status_code == 400
    assert "Cannot transition status from waitlist to cancelled" in resp1.json()["detail"]

    # 2. Waitlist -> Accepted is allowed
    resp2 = await client.patch(f"{BASE}{registration_id}", json={"status": "accepted"})
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "accepted"

    # 3. Accepted -> Waitlist is prohibited
    resp3 = await client.patch(f"{BASE}{registration_id}", json={"status": "waitlist"})
    assert resp3.status_code == 400
    assert "Cannot transition status from accepted to waitlist" in resp3.json()["detail"]

    # 4. Accepted -> Cancelled is allowed
    resp4 = await client.patch(f"{BASE}{registration_id}", json={"status": "cancelled"})
    assert resp4.status_code == 200
    assert resp4.json()["status"] == "cancelled"

    # 5. Cancelled -> Accepted (or anything else) is prohibited
    resp5 = await client.patch(f"{BASE}{registration_id}", json={"status": "accepted"})
    assert resp5.status_code == 400
    assert "Cannot transition status from cancelled to accepted" in resp5.json()["detail"]
