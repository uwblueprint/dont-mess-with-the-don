from datetime import datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.dependencies.auth import get_current_user, get_optional_user
from app.dependencies.services import get_event_service
from app.models.attendance import Attendance
from app.models.enum import RegistrationStatusEnum, UserRole
from app.models.event import Event, EventCreate, EventUpdate
from app.models.registration import Registration
from app.models.user import User

BASE = "/events"

VALID_FORM = {
    "formId": "frm_river_cleanup",
    "version": 1,
    "title": "River Cleanup Registration",
    "questions": [{"id": "q_name", "type": "short_answer", "label": "Name", "required": True}],
}


def make_event(**overrides):
    data = {
        "id": uuid4(),
        "name": "River Cleanup",
        "description": "Clean up the Don Valley shoreline.",
        "location": "Toronto",
        "max_attendees": 25,
        "event_status": "published",
        "event_type_id": uuid4(),
        "headline_image_key": "event-images/headline.jpg",
        "start_datetime": datetime(2026, 7, 15, 10, 0, 0),
        "end_datetime": datetime(2026, 7, 15, 12, 0, 0),
        "created_at": datetime(2026, 6, 1, 9, 0, 0),
        "updated_at": None,
        "post_event_photo_keys": ["events/e1/upload.jpg"],
        "notes": ["Bring gloves"],
        "form_json": VALID_FORM,
    }
    data.update(overrides)
    return Event(**data)


def event_request_payload(**overrides):
    data = make_event().model_dump(mode="json")
    data.pop("id")
    data.pop("created_at")
    data.pop("updated_at")
    data.pop("check_in_token")
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
        self.delete_event_error: Exception | None = None

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
        if self.delete_event_error:
            raise self.delete_event_error
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


async def test_create_event_invalid_form_json_returns_422(client, event_service):
    payload = event_request_payload(form_json={"fields": []})

    response = await client.post(BASE, json=payload)

    assert response.status_code == 422
    assert event_service.create_event_calls == []


async def test_update_event_invalid_form_json_returns_422(client, event_service):
    invalid_form = {
        **VALID_FORM,
        "questions": [{"id": "q_pick", "type": "multiple_choice", "label": "Pick"}],
    }

    response = await client.patch(f"{BASE}/{uuid4()}", json={"form_json": invalid_form})

    assert response.status_code == 422


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


async def test_update_event_ignores_recurrence(client, event_service):
    # recurrence lives on event_series, not events
    response = await client.patch(
        f"{BASE}/{uuid4()}", json={"location": "East York", "recurrence": "FREQ=WEEKLY"}
    )

    assert response.status_code == 200
    _, update_data = event_service.update_event_calls[0]
    assert update_data.model_dump(exclude_unset=True) == {"location": "East York"}


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


def make_event_with_token(check_in_token: str) -> Event:
    return make_event(check_in_token=check_in_token)


async def test_get_check_in_link_returns_frontend_url(client, event_service, monkeypatch):
    monkeypatch.setattr(settings, "frontend_url", "https://dmwtd.example.com")
    event = make_event_with_token("tok_abc-123")
    event_service.get_event_result = event

    response = await client.get(f"{BASE}/{event.id}/check-in-link")

    assert response.status_code == 200
    assert response.json() == {
        "url": f"https://dmwtd.example.com/check-in?event={event.id}&token=tok_abc-123"
    }
    assert event_service.get_event_calls == [event.id]


async def test_get_check_in_link_handles_trailing_slash_in_frontend_url(
    client, event_service, monkeypatch
):
    monkeypatch.setattr(settings, "frontend_url", "https://dmwtd.example.com/")
    event = make_event_with_token("tok")
    event_service.get_event_result = event

    response = await client.get(f"{BASE}/{event.id}/check-in-link")

    assert response.json()["url"].startswith("https://dmwtd.example.com/check-in?")


async def test_get_check_in_link_nonexistent_event_returns_404(client, event_service):
    event_service.get_event_result = None

    response = await client.get(f"{BASE}/{uuid4()}/check-in-link")

    assert response.status_code == 404


async def test_get_check_in_link_requires_admin(app, client, event_service):
    attendee = User(id=1, email="sam@example.com", role=UserRole.ATTENDEE)
    app.dependency_overrides[get_current_user] = lambda: attendee

    response = await client.get(f"{BASE}/{uuid4()}/check-in-link")

    assert response.status_code == 403
    assert event_service.get_event_calls == []


async def test_get_check_in_link_requires_login(app, client, event_service):
    app.dependency_overrides.pop(get_current_user)

    response = await client.get(f"{BASE}/{uuid4()}/check-in-link")

    assert response.status_code == 401
    assert event_service.get_event_calls == []


async def test_get_events_does_not_expose_check_in_token(client, event_service):
    event_service.events = [make_event_with_token("secret-token-list")]

    response = await client.get(BASE)

    assert response.status_code == 200
    assert "check_in_token" not in response.json()[0]
    assert "secret-token-list" not in response.text


async def test_get_event_by_id_does_not_expose_check_in_token(client, event_service):
    event = make_event_with_token("secret-token-detail")
    event_service.get_event_result = event

    response = await client.get(f"{BASE}/{event.id}")

    assert response.status_code == 200
    assert "check_in_token" not in response.json()
    assert "secret-token-detail" not in response.text


async def test_event_response_resolves_urls_and_hides_keys(client, event_service):
    body = (await client.get(BASE)).json()[0]
    assert body["headline_image_url"] == "https://public.test/event-images/headline.jpg"
    assert body["post_event_photo_urls"] == [
        "https://private.test/events/e1/upload.jpg?expires=3600"
    ]
    assert "headline_image_key" not in body
    assert "post_event_photo_keys" not in body


async def test_anonymous_event_response_omits_post_event_photos(app, client, event_service):
    app.dependency_overrides[get_optional_user] = lambda: None

    for url in (BASE, f"{BASE}/{event_service.events[0].id}"):
        response = await client.get(url)
        body = response.json()
        event = body[0] if isinstance(body, list) else body
        assert event["headline_image_url"] == "https://public.test/event-images/headline.jpg"
        assert event["post_event_photo_urls"] == []


async def test_create_event_rejects_url_as_image_key(client, event_service):
    response = await client.post(
        BASE, json=event_request_payload(headline_image_key="https://example.com/a.jpg")
    )
    assert response.status_code == 422


async def test_delete_event_with_signed_waivers_returns_409(client, event_service):
    # waiver_signed.event_id is ON DELETE RESTRICT
    event_service.delete_event_error = IntegrityError("DELETE", {}, Exception("fk"))

    response = await client.delete(f"{BASE}/{uuid4()}")

    assert response.status_code == 409


# --- Post-event photo access: admins and the event's attendees only ---

ATTENDEE_ID = 101
GUARDIAN_ID = 102
CHILD_ID = 103
STRANGER_ID = 104
PHOTO_URL = "https://private.test/events/e1/upload.jpg?expires=3600"


@pytest_asyncio.fixture
async def db(app, client):
    from app.models import get_session

    # Keep the generator referenced (yield, not return) so the session stays open
    session_gen = app.dependency_overrides[get_session]()
    session = await session_gen.__anext__()
    session.add_all(
        [
            User(id=ATTENDEE_ID, email="attendee@example.com"),
            User(id=GUARDIAN_ID, email="guardian@example.com"),
            User(id=CHILD_ID, email="child@example.com", guardian_id=GUARDIAN_ID),
            User(id=STRANGER_ID, email="stranger@example.com"),
        ]
    )
    await session.commit()
    yield session
    await session_gen.aclose()


def login_as(app, user_id):
    user = User(id=user_id, email=f"{user_id}@example.com", role=UserRole.ATTENDEE)
    app.dependency_overrides[get_optional_user] = lambda: user


async def register(db, user_id, event_id, status=RegistrationStatusEnum.ACCEPTED):
    db.add(Registration(user_id=user_id, event_instance_id=event_id, status=status))
    await db.commit()


async def photos_for(client, event_id):
    response = await client.get(f"{BASE}/{event_id}")
    assert response.status_code == 200
    return response.json()["post_event_photo_urls"]


async def test_accepted_registrant_sees_photos(app, client, event_service, db):
    event_id = event_service.events[0].id
    await register(db, ATTENDEE_ID, event_id)
    login_as(app, ATTENDEE_ID)
    assert await photos_for(client, event_id) == [PHOTO_URL]


@pytest.mark.parametrize(
    "status", [RegistrationStatusEnum.WAITLIST, RegistrationStatusEnum.CANCELLED]
)
async def test_waitlisted_or_cancelled_registrant_gets_no_photos(
    app, client, event_service, db, status
):
    event_id = event_service.events[0].id
    await register(db, ATTENDEE_ID, event_id, status)
    login_as(app, ATTENDEE_ID)
    assert await photos_for(client, event_id) == []


async def test_unrelated_logged_in_user_gets_no_photos(app, client, event_service, db):
    event_id = event_service.events[0].id
    await register(db, ATTENDEE_ID, event_id)
    login_as(app, STRANGER_ID)
    assert await photos_for(client, event_id) == []


async def test_guardian_of_accepted_child_sees_photos(app, client, event_service, db):
    event_id = event_service.events[0].id
    await register(db, CHILD_ID, event_id)
    login_as(app, GUARDIAN_ID)
    assert await photos_for(client, event_id) == [PHOTO_URL]


async def test_check_in_without_registration_sees_photos(app, client, event_service, db):
    event_id = event_service.events[0].id
    db.add(Attendance(user_id=ATTENDEE_ID, event_instance_id=event_id))
    await db.commit()
    login_as(app, ATTENDEE_ID)
    assert await photos_for(client, event_id) == [PHOTO_URL]


async def test_event_list_signs_photos_only_for_events_attended(app, client, event_service, db):
    attended, other = make_event(), make_event()
    event_service.events = [attended, other]
    await register(db, ATTENDEE_ID, attended.id)
    login_as(app, ATTENDEE_ID)

    body = {e["id"]: e["post_event_photo_urls"] for e in (await client.get(BASE)).json()}

    assert body == {str(attended.id): [PHOTO_URL], str(other.id): []}
