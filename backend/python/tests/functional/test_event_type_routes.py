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


VALID_FORM = {
    "formId": "frm_poker_night",
    "version": 1,
    "title": "Poker Night Registration",
    "questions": [
        {"id": "q_name", "type": "short_answer", "label": "Name", "required": True},
        {
            "id": "q_experience",
            "type": "multiple_choice",
            "label": "Experience level",
            "options": [
                {"id": "opt_new", "label": "New"},
                {"id": "opt_pro", "label": "Pro"},
            ],
        },
    ],
}


async def test_create_event_type_with_form_json_returns_201(client):
    payload = {**VALID_PAYLOAD, "name": "Poker Night With Form", "form_json": VALID_FORM}
    response = await client.post(BASE, json=payload)
    assert response.status_code == 201
    assert response.json()["form_json"]["questions"][1]["options"][0]["id"] == "opt_new"


async def test_create_event_type_without_form_json_defaults_to_empty(client):
    response = await client.post(BASE, json={**VALID_PAYLOAD, "name": "Poker Night No Form"})
    assert response.status_code == 201
    assert response.json()["form_json"] == {}


async def test_create_event_type_invalid_form_json_returns_422(client):
    payload = {
        **VALID_PAYLOAD,
        "name": "Poker Night Bad Form",
        "form_json": {"waiver_required": True},
    }
    response = await client.post(BASE, json=payload)
    assert response.status_code == 422


async def test_update_event_type_invalid_form_json_returns_422(client):
    created = await client.post(BASE, json={**VALID_PAYLOAD, "name": "Poker Night Patch"})
    assert created.status_code == 201

    duplicate_ids = {**VALID_FORM, "questions": [VALID_FORM["questions"][0]] * 2}
    response = await client.patch(
        f"{BASE}{created.json()['id']}", json={"form_json": duplicate_ids}
    )
    assert response.status_code == 422
