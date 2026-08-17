from datetime import datetime
from uuid import UUID, uuid4

import pytest

from app.dependencies.services import get_event_service
from app.models.event import EventCreate, EventRead, EventUpdate

BASE = "/events"


def make_event(**overrides):
    data = {
        "id": uuid4(),
        "name": "River Cleanup",
        "description": "Clean up the Don Valley shoreline.",
        "location": "Toronto",
        "max_attendees": 25,
        "event_status": "published",
        "event_type_id": uuid4(),
        "image": "https://example.com/headline.jpg",
        "start_datetime": datetime(2026, 7, 15, 10, 0, 0),
        "end_datetime": datetime(2026, 7, 15, 12, 0, 0),
        "created_at": datetime(2026, 6, 1, 9, 0, 0),
        "updated_at": None,
        "image_urls": ["https://example.com/upload.jpg"],
        "notes": ["Bring gloves"],
        "form_json": {"fields": []},
    }
    data.update(overrides)
    return EventRead(**data)


def event_request_payload(**overrides):
    data = make_event().model_dump(mode="json")
    data.pop("id")
    data.pop("created_at")
    data.pop("updated_at")
    data.update(overrides)
    return data


class FakeEventService:
    def __init__(self):
        self.events = [make_event()]
        self.get_events_calls = []
        self.get_event_calls = []
        self.create_event_calls = []
        self.update_event_calls = []
        self.delete_event_calls = []
        self.get_event_result = self.events[0]
        self.create_event_result = self.events[0]
        self.update_event_result = self.events[0]
        self.delete_event_result = True

    async def get_events(self, session, **filters):
        self.get_events_calls.append(filters)
        return self.events

    async def get_event(self, session, event_id: UUID):
        self.get_event_calls.append(event_id)
        return self.get_event_result

    async def create_event(self, session, event_data: EventCreate):
        self.create_event_calls.append(event_data)
        return self.create_event_result

    async def update_event(self, session, event_id: UUID, event_data: EventUpdate):
        self.update_event_calls.append((event_id, event_data))
        return self.update_event_result

    async def delete_event(self, session, event_id: UUID):
        self.delete_event_calls.append(event_id)
        return self.delete_event_result


@pytest.fixture
def event_service(app):
    service = FakeEventService()
    app.dependency_overrides[get_event_service] = lambda: service
    return service


async def test_get_events_returns_200(client, event_service):
    response = await client.get(BASE)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "River Cleanup"
    assert event_service.get_events_calls == [
        {
            "status": None,
            "event_type": None,
            "location": None,
            "starts_after": None,
            "starts_before": None,
        }
    ]


async def test_get_events_passes_query_filters_to_service(client, event_service):
    event_type_id = uuid4()

    response = await client.get(
        BASE,
        params={
            "status": "published",
            "event_type": str(event_type_id),
            "location": "Toronto",
            "starts_after": "2026-07-01",
            "starts_before": "2026-08-01",
        },
    )

    assert response.status_code == 200
    assert event_service.get_events_calls == [
        {
            "status": "published",
            "event_type": event_type_id,
            "location": "Toronto",
            "starts_after": datetime(2026, 7, 1, 0, 0, 0),
            "starts_before": datetime(2026, 8, 1, 23, 59, 59, 999999),
        }
    ]


async def test_get_events_invalid_event_type_returns_422(client, event_service):
    response = await client.get(BASE, params={"event_type": "not-a-uuid"})

    assert response.status_code == 422
    assert event_service.get_events_calls == []


async def test_get_events_invalid_date_returns_422(client, event_service):
    response = await client.get(BASE, params={"starts_after": "tomorrow"})

    assert response.status_code == 422
    assert event_service.get_events_calls == []


async def test_create_event_returns_201(client, event_service):
    payload = event_request_payload(name="Tree Planting")

    response = await client.post(BASE, json=payload)

    assert response.status_code == 201
    assert response.json()["name"] == "River Cleanup"
    assert len(event_service.create_event_calls) == 1
    assert event_service.create_event_calls[0].name == "Tree Planting"


async def test_get_event_by_id_returns_200(client, event_service):
    event_id = uuid4()

    response = await client.get(f"{BASE}/{event_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(event_service.get_event_result.id)
    assert event_service.get_event_calls == [event_id]


async def test_get_nonexistent_event_returns_404(client, event_service):
    event_service.get_event_result = None

    response = await client.get(f"{BASE}/{uuid4()}")

    assert response.status_code == 404


async def test_update_event_returns_200(client, event_service):
    event_id = uuid4()

    response = await client.patch(f"{BASE}/{event_id}", json={"location": "East York"})

    assert response.status_code == 200
    assert response.json()["name"] == "River Cleanup"
    assert len(event_service.update_event_calls) == 1
    called_event_id, update_data = event_service.update_event_calls[0]
    assert called_event_id == event_id
    assert update_data.location == "East York"


async def test_update_nonexistent_event_returns_404(client, event_service):
    event_service.update_event_result = None

    response = await client.patch(f"{BASE}/{uuid4()}", json={"location": "East York"})

    assert response.status_code == 404


async def test_delete_event_returns_204(client, event_service):
    event_id = uuid4()

    response = await client.delete(f"{BASE}/{event_id}")

    assert response.status_code == 204
    assert event_service.delete_event_calls == [event_id]


async def test_delete_nonexistent_event_returns_404(client, event_service):
    event_service.delete_event_result = False

    response = await client.delete(f"{BASE}/{uuid4()}")

    assert response.status_code == 404
