BASE = "/event-types/"


async def test_create_event_type_returns_201(client):
    response = await client.post(
        BASE,
        json={
            "name": "Test Event Type",
            "image": "http://example.com/image.png",
            "description": "A test event type",
            "location": "Test Location",
            "max_attendees": 100,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Event Type"
    assert "id" in data


async def test_create_event_type_duplicate_name_returns_409(client):
    await client.post(
        BASE,
        json={
            "name": "Test Event Type",
            "image": "http://example.com/image.png",
            "description": "A test event type",
            "location": "Test Location",
            "max_attendees": 100,
        },
    )
    response = await client.post(
        BASE,
        json={
            "name": "Test Event Type",
            "image": "http://example.com/image.png",
            "description": "A test event type",
            "location": "Test Location",
            "max_attendees": 100,
        },
    )
    assert response.status_code == 409


async def test_create_event_type_invalid_data_returns_422(client):
    response = await client.post(
        BASE,
        json={
            "name": "Test Event Type",
            "image": "not-a-url",
            "description": "A test event type",
            "location": "Test Location",
            "max_attendees": 100,
        },
    )
    assert response.status_code == 422


async def test_get_event_types_returns_200(client):
    await client.post(
        BASE,
        json={
            "name": "Test Event Type",
            "image": "http://example.com/image.png",
            "description": "A test event type",
            "location": "Test Location",
            "max_attendees": 100,
        },
    )
    response = await client.get(BASE)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


async def test_get_event_type_by_id_returns_200(client):
    create = await client.post(
        BASE,
        json={
            "name": "Test Event Type",
            "image": "http://example.com/image.png",
            "description": "A test event type",
            "location": "Test Location",
            "max_attendees": 100,
        },
    )
    event_type_id = create.json()["id"]
    response = await client.get(f"{BASE}{event_type_id}")
    assert response.status_code == 200
    assert response.json()["id"] == event_type_id


async def test_get_nonexistent_event_type_returns_404(client):
    response = await client.get(f"{BASE}99999")
    assert response.status_code == 404


async def test_update_event_type_returns_200(client):
    create = await client.post(
        BASE,
        json={
            "name": "Test Event Type",
            "image": "http://example.com/image.png",
            "description": "A test event type",
            "location": "Test Location",
            "max_attendees": 100,
        },
    )
    event_type_id = create.json()["id"]
    response = await client.patch(
        f"{BASE}{event_type_id}", json={"description": "Updated description"}
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"


async def test_update_nonexistent_event_type_returns_404(client):
    response = await client.patch(f"{BASE}99999", json={"description": "Updated description"})
    assert response.status_code == 404


async def test_delete_event_type_returns_204(client):
    create = await client.post(
        BASE,
        json={
            "name": "Test Event Type",
            "image": "http://example.com/image.png",
            "description": "A test event type",
            "location": "Test Location",
            "max_attendees": 100,
        },
    )
    event_type_id = create.json()["id"]
    response = await client.delete(f"{BASE}{event_type_id}")
    assert response.status_code == 204


async def test_delete_nonexistent_event_type_returns_404(client):
    response = await client.delete(f"{BASE}99999")
    assert response.status_code == 404
