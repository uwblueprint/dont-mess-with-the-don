import uuid

import pytest

BASE = "/event-series/"


def _test_payload(**overrides):
    payload = {
        "recurrence": "FREQ=WEEKLY",
        "is_active": True,
        "name": "Test Event Series",
        "description": "A test event series",
        "location": "Test Location",
        "max_attendees": 10,
        "max_waitlist": 5,
        "event_status": "active",
        "headline_image_key": "event-images/test.png",
        "start_time": "10:00:00",
        "end_time": "12:00:00",
        "registration_type": "lottery",
    }
    payload.update(overrides)
    return payload


async def test_create_event_series_returns_201(client):
    response = await client.post(BASE, json=_test_payload(recurrence="FREQ=WEEKLY"))
    assert response.status_code == 201
    data = response.json()
    assert data["recurrence"] == "FREQ=WEEKLY"
    assert data["is_active"] is True
    assert "id" in data


async def test_create_event_series_with_is_active_returns_201(client):
    response = await client.post(BASE, json=_test_payload(recurrence="FREQ=DAILY", is_active=False))
    assert response.status_code == 201
    assert response.json()["is_active"] is False


async def test_create_event_series_missing_recurrence_returns_422(client):
    payload = _test_payload()
    del payload["recurrence"]
    response = await client.post(BASE, json=payload)
    assert response.status_code == 422


async def test_create_event_series_empty_recurrence_returns_422(client):
    response = await client.post(BASE, json=_test_payload(recurrence=""))
    assert response.status_code == 422


async def test_create_event_series_invalid_recurrence_returns_422(client):
    response = await client.post(BASE, json=_test_payload(recurrence="not a recurrence rule"))
    assert response.status_code == 422


@pytest.mark.parametrize(
    "recurrence",
    [
        "FREQ=SECONDLY",
        "FREQ=MINUTELY",
        "FREQ=HOURLY",
        "FREQ=DAILY;INTERVAL=0",
        "FREQ=DAILY;BYHOUR=9,10",
        "DTSTART:20260101T090000Z\nRRULE:FREQ=DAILY",
        "DTSTART:20260101T090000",
    ],
)
async def test_create_event_series_unsupported_recurrence_returns_422(client, recurrence):
    response = await client.post(BASE, json=_test_payload(recurrence=recurrence))
    assert response.status_code == 422


@pytest.mark.parametrize(
    "recurrence",
    ["FREQ=WEEKLY;BYDAY=SA", "RRULE:FREQ=DAILY;INTERVAL=2", "FREQ=MONTHLY;BYMONTHDAY=1"],
)
async def test_create_event_series_supported_recurrence_returns_201(client, recurrence):
    response = await client.post(BASE, json=_test_payload(recurrence=recurrence))
    assert response.status_code == 201


async def test_update_event_series_unsupported_recurrence_returns_422(client):
    created = await client.post(BASE, json=_test_payload())
    response = await client.patch(
        f"{BASE}{created.json()['id']}", json={"recurrence": "FREQ=MINUTELY"}
    )
    assert response.status_code == 422


async def test_get_event_series_list_returns_200(client):
    await client.post(BASE, json=_test_payload(recurrence="FREQ=WEEKLY"))
    response = await client.get(BASE)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


async def test_get_event_series_by_id_returns_200(client):
    create = await client.post(BASE, json=_test_payload(recurrence="FREQ=MONTHLY"))
    event_series_id = create.json()["id"]
    response = await client.get(f"{BASE}{event_series_id}")
    assert response.status_code == 200
    assert response.json()["id"] == event_series_id


async def test_get_nonexistent_event_series_returns_404(client):
    response = await client.get(f"{BASE}{uuid.uuid4()}")
    assert response.status_code == 404


async def test_update_event_series_returns_200(client):
    create = await client.post(BASE, json=_test_payload(recurrence="FREQ=WEEKLY"))
    event_series_id = create.json()["id"]
    response = await client.patch(f"{BASE}{event_series_id}", json={"recurrence": "FREQ=DAILY"})
    assert response.status_code == 200
    assert response.json()["recurrence"] == "FREQ=DAILY"


async def test_update_event_series_is_active_returns_200(client):
    create = await client.post(BASE, json=_test_payload(recurrence="FREQ=WEEKLY"))
    event_series_id = create.json()["id"]
    response = await client.patch(f"{BASE}{event_series_id}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_update_nonexistent_event_series_returns_404(client):
    response = await client.patch(f"{BASE}{uuid.uuid4()}", json={"recurrence": "FREQ=DAILY"})
    assert response.status_code == 404


async def test_delete_event_series_returns_204(client):
    create = await client.post(BASE, json=_test_payload(recurrence="FREQ=WEEKLY"))
    event_series_id = create.json()["id"]
    response = await client.delete(f"{BASE}{event_series_id}")
    assert response.status_code == 204


async def test_delete_nonexistent_event_series_returns_404(client):
    response = await client.delete(f"{BASE}{uuid.uuid4()}")
    assert response.status_code == 404


async def test_event_series_has_no_post_event_photos(client):
    response = await client.post(
        BASE,
        json=_test_payload(recurrence="FREQ=WEEKLY", post_event_photo_keys=["events/x/a.jpg"]),
    )
    assert response.status_code == 201
    body = response.json()
    assert not [field for field in body if field.startswith("post_event_photo")]
    listed = (await client.get(BASE)).json()
    assert not [field for item in listed for field in item if field.startswith("post_event_photo")]
