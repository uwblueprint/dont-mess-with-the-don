import uuid

BASE = "/attendance/"


async def create_attendance_payload(client, email: str, event_id: str | None = None) -> dict:
    user_response = await client.post("/users/", json={"email": email})
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    return {
        "user_id": user_id,
        "event_instance_id": event_id or str(uuid.uuid4()),
    }


async def test_create_attendance_returns_201(client):
    payload = await create_attendance_payload(client, "attendance_create@example.com")

    response = await client.post(BASE, json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == payload["user_id"]
    assert data["event_instance_id"] == payload["event_instance_id"]
    assert "id" in data


async def test_duplicate_attendance_returns_409(client):
    payload = await create_attendance_payload(client, "attendance_duplicate@example.com")

    first_response = await client.post(BASE, json=payload)
    assert first_response.status_code == 201

    response = await client.post(BASE, json=payload)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


async def test_get_attendance_list_returns_200(client):
    payload = await create_attendance_payload(client, "attendance_list@example.com")
    await client.post(BASE, json=payload)

    response = await client.get(BASE)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


async def test_get_attendance_by_id_returns_200(client):
    payload = await create_attendance_payload(client, "attendance_get@example.com")
    create_response = await client.post(BASE, json=payload)
    attendance_id = create_response.json()["id"]

    response = await client.get(f"{BASE}{attendance_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == attendance_id
    assert data["user_id"] == payload["user_id"]
    assert data["event_instance_id"] == payload["event_instance_id"]


async def test_get_nonexistent_attendance_returns_404(client):
    response = await client.get(f"{BASE}99999")

    assert response.status_code == 404


async def test_delete_attendance_success(client):
    payload = await create_attendance_payload(client, "attendance_delete@example.com")
    create_response = await client.post(BASE, json=payload)
    attendance_id = create_response.json()["id"]

    delete_response = await client.delete(f"{BASE}{attendance_id}")

    assert delete_response.status_code == 204

    get_response = await client.get(f"{BASE}{attendance_id}")
    assert get_response.status_code == 404


async def test_delete_nonexistent_attendance_returns_404(client):
    response = await client.delete(f"{BASE}99999")

    assert response.status_code == 404


async def test_get_attendance_filtering(client):
    event_id1 = str(uuid.uuid4())
    event_id2 = str(uuid.uuid4())

    payload1 = await create_attendance_payload(client, "attendance_filter1@example.com", event_id1)
    payload2 = await create_attendance_payload(client, "attendance_filter2@example.com", event_id1)
    payload3 = await create_attendance_payload(client, "attendance_filter3@example.com", event_id2)

    await client.post(BASE, json=payload1)
    await client.post(BASE, json=payload2)
    await client.post(BASE, json=payload3)

    response_user = await client.get(f"{BASE}?user_id={payload1['user_id']}")
    assert response_user.status_code == 200
    data = response_user.json()
    assert len(data) == 1
    assert data[0]["user_id"] == payload1["user_id"]

    response_event = await client.get(f"{BASE}?event_instance_id={event_id1}")
    assert response_event.status_code == 200
    data = response_event.json()
    assert len(data) == 2
    assert all(record["event_instance_id"] == event_id1 for record in data)

    response_multi = await client.get(
        f"{BASE}?user_id={payload2['user_id']}&event_instance_id={event_id1}"
    )
    assert response_multi.status_code == 200
    data = response_multi.json()
    assert len(data) == 1
    assert data[0]["user_id"] == payload2["user_id"]
    assert data[0]["event_instance_id"] == event_id1


async def test_get_attendance_invalid_event_instance_id_returns_422(client):
    response = await client.get(f"{BASE}?event_instance_id=not-a-uuid")

    assert response.status_code == 422
