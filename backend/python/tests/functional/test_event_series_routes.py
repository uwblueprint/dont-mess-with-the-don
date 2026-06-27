import uuid

BASE = "/event-series/"


async def test_create_event_series_returns_201(client):
    response = await client.post(BASE, json={"recurrence": "FREQ=WEEKLY"})
    assert response.status_code == 201
    data = response.json()
    assert data["recurrence"] == "FREQ=WEEKLY"
    assert data["is_active"] is True
    assert "id" in data


async def test_create_event_series_with_is_active_returns_201(client):
    response = await client.post(BASE, json={"recurrence": "FREQ=DAILY", "is_active": False})
    assert response.status_code == 201
    assert response.json()["is_active"] is False


async def test_create_event_series_missing_recurrence_returns_422(client):
    response = await client.post(BASE, json={"is_active": True})
    assert response.status_code == 422


async def test_create_event_series_empty_recurrence_returns_422(client):
    response = await client.post(BASE, json={"recurrence": ""})
    assert response.status_code == 422


async def test_get_event_series_list_returns_200(client):
    await client.post(BASE, json={"recurrence": "FREQ=WEEKLY"})
    response = await client.get(BASE)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


async def test_get_event_series_by_id_returns_200(client):
    create = await client.post(BASE, json={"recurrence": "FREQ=MONTHLY"})
    event_series_id = create.json()["id"]
    response = await client.get(f"{BASE}{event_series_id}")
    assert response.status_code == 200
    assert response.json()["id"] == event_series_id


async def test_get_nonexistent_event_series_returns_404(client):
    response = await client.get(f"{BASE}{uuid.uuid4()}")
    assert response.status_code == 404


async def test_update_event_series_returns_200(client):
    create = await client.post(BASE, json={"recurrence": "FREQ=WEEKLY"})
    event_series_id = create.json()["id"]
    response = await client.patch(f"{BASE}{event_series_id}", json={"recurrence": "FREQ=DAILY"})
    assert response.status_code == 200
    assert response.json()["recurrence"] == "FREQ=DAILY"


async def test_update_event_series_is_active_returns_200(client):
    create = await client.post(BASE, json={"recurrence": "FREQ=WEEKLY"})
    event_series_id = create.json()["id"]
    response = await client.patch(f"{BASE}{event_series_id}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_update_nonexistent_event_series_returns_404(client):
    response = await client.patch(f"{BASE}{uuid.uuid4()}", json={"recurrence": "FREQ=DAILY"})
    assert response.status_code == 404


async def test_delete_event_series_returns_204(client):
    create = await client.post(BASE, json={"recurrence": "FREQ=WEEKLY"})
    event_series_id = create.json()["id"]
    response = await client.delete(f"{BASE}{event_series_id}")
    assert response.status_code == 204


async def test_delete_nonexistent_event_series_returns_404(client):
    response = await client.delete(f"{BASE}{uuid.uuid4()}")
    assert response.status_code == 404
