from uuid import uuid4

BASE = "/event-types/"

VALID_PAYLOAD = {
    "name": "Poker Night",
    "image": "https://example.com/poker.png",
    "description": "A friendly game of poker",
    "location": "Toronto",
    "max_attendees": 8,
}


async def test_create_event_type_returns_201(client):
    response = await client.post(BASE, json=VALID_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Poker Night"
    assert "id" in data


async def test_create_event_type_missing_required_field_returns_422(client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "name"}
    response = await client.post(BASE, json=payload)
    assert response.status_code == 422


async def test_create_event_type_negative_max_attendees_returns_422(client):
    payload = {**VALID_PAYLOAD, "max_attendees": -1}
    response = await client.post(BASE, json=payload)
    assert response.status_code == 422


async def test_create_event_type_invalid_image_url_returns_422(client):
    payload = {**VALID_PAYLOAD, "image": "not-a-url"}
    response = await client.post(BASE, json=payload)
    assert response.status_code == 422


async def test_get_event_types_returns_200(client):
    await client.post(BASE, json=VALID_PAYLOAD)
    response = await client.get(BASE)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


async def test_get_event_type_by_id_returns_200(client):
    create = await client.post(BASE, json=VALID_PAYLOAD)
    event_type_id = create.json()["id"]
    response = await client.get(f"{BASE}{event_type_id}")
    assert response.status_code == 200
    assert response.json()["id"] == event_type_id


async def test_get_nonexistent_event_type_returns_404(client):
    response = await client.get(f"{BASE}{uuid4()}")
    assert response.status_code == 404


async def test_update_event_type_returns_200(client):
    create = await client.post(BASE, json=VALID_PAYLOAD)
    event_type_id = create.json()["id"]
    response = await client.patch(f"{BASE}{event_type_id}", json={"location": "Waterloo"})
    assert response.status_code == 200
    assert response.json()["location"] == "Waterloo"


async def test_update_nonexistent_event_type_returns_404(client):
    response = await client.patch(f"{BASE}{uuid4()}", json={"location": "Waterloo"})
    assert response.status_code == 404


async def test_delete_event_type_returns_204(client):
    create = await client.post(BASE, json=VALID_PAYLOAD)
    event_type_id = create.json()["id"]
    response = await client.delete(f"{BASE}{event_type_id}")
    assert response.status_code == 204


async def test_delete_nonexistent_event_type_returns_404(client):
    response = await client.delete(f"{BASE}{uuid4()}")
    assert response.status_code == 404
