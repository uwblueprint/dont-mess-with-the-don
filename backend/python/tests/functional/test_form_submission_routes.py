import copy
import json
import uuid

from sqlalchemy import inspect, text
from sqlalchemy.dialects import sqlite

from app.models.event import Event

BASE = "/form-submissions/"

WORKSHOP_FORM = {
    "formId": "frm_workshop_signup",
    "version": 1,
    "title": "Workshop Registration",
    "sections": [
        {
            "id": "sec_intro",
            "title": "About you",
            "questions": [
                {"id": "q_name", "type": "short_answer", "label": "Name", "required": True},
                {
                    "id": "q_attending",
                    "type": "multiple_choice",
                    "label": "Will you attend in person or virtually?",
                    "required": True,
                    "options": [
                        {"id": "opt_inperson", "label": "In person", "goToSection": "sec_inperson"},
                        {"id": "opt_virtual", "label": "Virtually", "goToSection": "sec_virtual"},
                    ],
                },
            ],
            "defaultNext": "sec_inperson",
        },
        {
            "id": "sec_inperson",
            "title": "In-person details",
            "questions": [
                {"id": "q_arrival", "type": "time", "label": "Arrival time", "required": False}
            ],
            "defaultNext": None,
        },
        {
            "id": "sec_virtual",
            "title": "Virtual details",
            "questions": [
                {
                    "id": "q_zoom_email",
                    "type": "email",
                    "label": "Email for the Zoom invite",
                    "required": True,
                }
            ],
            "defaultNext": None,
        },
    ],
}

VALID_RESPONSE = {
    "formId": "frm_workshop_signup",
    "formVersion": 1,
    "path": ["sec_intro", "sec_inperson"],
    "answers": {"q_name": "Ben Ng", "q_attending": "opt_inperson", "q_arrival": "18:30"},
}


def _uuid_to_db(value: uuid.UUID) -> str:
    """Convert a UUID to how the sqlite test database stores it"""
    processor = inspect(Event).columns["id"].type.bind_processor(sqlite.dialect())
    return processor(value) if processor else str(value)


async def create_event_type(session_maker, form_json=None) -> uuid.UUID:
    """Insert an event_types row directly (there are no event type routes yet)"""
    event_type_id = uuid.uuid4()
    async with session_maker() as session:
        await session.execute(
            text(
                "INSERT INTO event_types (id, name, image, description, location, "
                "max_attendees, cancellation_cutoff_hours, form_json, created_at, updated_at) "
                "VALUES (:id, 'Workshop', 'img.png', 'A workshop', 'The Don', 20, 48, "
                ":form_json, '2026-07-01 12:00:00', NULL)"
            ),
            {
                "id": _uuid_to_db(event_type_id),
                "form_json": json.dumps(form_json if form_json is not None else {}),
            },
        )
        await session.commit()
    return event_type_id


async def create_event(session_maker, form_json=None, event_type_id=None) -> uuid.UUID:
    """Insert an events row directly (there are no event routes yet).

    Raw SQL is used because the ARRAY columns cannot be bound through the
    ORM on the sqlite test database.
    """
    event_id = uuid.uuid4()
    async with session_maker() as session:
        await session.execute(
            text(
                "INSERT INTO events (id, name, description, location, max_attendees, "
                "event_status, event_type, image, start_time, end_time, image_urls, notes, "
                "recurrence, form_json, created_at, updated_at) "
                "VALUES (:id, 'Year End Celebration', 'Celebrate', 'The Don', 50, 'active', "
                ":event_type, 'img.png', '2026-11-29 18:00:00', '2026-11-29 21:00:00', "
                "'{}', '{}', 'none', :form_json, '2026-07-01 12:00:00', NULL)"
            ),
            {
                "id": _uuid_to_db(event_id),
                "event_type": _uuid_to_db(event_type_id) if event_type_id else None,
                "form_json": json.dumps(form_json) if form_json is not None else None,
            },
        )
        await session.commit()
    return event_id


async def create_user(client, email: str) -> int:
    response = await client.post("/users/", json={"email": email})
    assert response.status_code == 201
    return response.json()["id"]


async def test_submit_form_returns_201(client, session_maker):
    user_id = await create_user(client, "submitter@example.com")
    event_id = await create_event(session_maker, form_json=WORKSHOP_FORM)

    response = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(event_id),
            "response_json": VALID_RESPONSE,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user_id
    assert data["event_instance_id"] == str(event_id)
    assert data["response_json"]["answers"]["q_name"] == "Ben Ng"
    assert data["response_json"]["responseVersion"] == 1


async def test_resubmit_edits_existing_submission(client, session_maker):
    user_id = await create_user(client, "resubmitter@example.com")
    event_id = await create_event(session_maker, form_json=WORKSHOP_FORM)

    payload = {
        "user_id": user_id,
        "event_instance_id": str(event_id),
        "response_json": VALID_RESPONSE,
    }
    first = await client.post(BASE, json=payload)
    assert first.status_code == 201
    submission_id = first.json()["id"]

    edited = copy.deepcopy(payload)
    edited["response_json"]["answers"]["q_name"] = "Benjamin Ng"
    second = await client.post(BASE, json=edited)
    assert second.status_code == 200
    data = second.json()
    assert data["id"] == submission_id
    assert data["response_json"]["answers"]["q_name"] == "Benjamin Ng"
    assert data["response_json"]["responseVersion"] == 2

    # Still only one submission for this user and event
    listing = await client.get(f"{BASE}?user_id={user_id}&event_instance_id={event_id}")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_submit_falls_back_to_event_type_template(client, session_maker):
    user_id = await create_user(client, "template@example.com")
    event_type_id = await create_event_type(session_maker, form_json=WORKSHOP_FORM)
    event_id = await create_event(session_maker, form_json=None, event_type_id=event_type_id)

    response = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(event_id),
            "response_json": VALID_RESPONSE,
        },
    )
    assert response.status_code == 201


async def test_submit_to_nonexistent_event_returns_404(client):
    user_id = await create_user(client, "noevent@example.com")

    response = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(uuid.uuid4()),
            "response_json": VALID_RESPONSE,
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


async def test_submit_to_event_without_form_returns_400(client, session_maker):
    user_id = await create_user(client, "noform@example.com")
    event_id = await create_event(session_maker, form_json=None)

    response = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(event_id),
            "response_json": VALID_RESPONSE,
        },
    )
    assert response.status_code == 400
    assert "does not have a registration form" in response.json()["detail"]


async def test_submit_invalid_response_returns_400(client, session_maker):
    user_id = await create_user(client, "invalid@example.com")
    event_id = await create_event(session_maker, form_json=WORKSHOP_FORM)

    # Missing required q_name, and path contradicts the conditional answer
    invalid = {
        "formId": "frm_workshop_signup",
        "formVersion": 1,
        "path": ["sec_intro", "sec_virtual"],
        "answers": {"q_attending": "opt_inperson", "q_zoom_email": "ben@example.com"},
    }
    response = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(event_id),
            "response_json": invalid,
        },
    )
    assert response.status_code == 400


async def test_submit_malformed_response_shape_returns_422(client, session_maker):
    """A response that isn't even shaped like a FormResponse is rejected at the model level"""
    user_id = await create_user(client, "malformed@example.com")
    event_id = await create_event(session_maker, form_json=WORKSHOP_FORM)

    response = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(event_id),
            "response_json": {"answers": {"q_name": "Ben"}},  # missing formId/formVersion/path
        },
    )
    assert response.status_code == 422


async def test_submit_links_registration_response_id(client, session_maker):
    user_id = await create_user(client, "linked@example.com")
    event_id = await create_event(session_maker, form_json=WORKSHOP_FORM)

    reg_response = await client.post(
        "/registrations/",
        json={"user_id": user_id, "event_instance_id": str(event_id), "status": "waitlist"},
    )
    assert reg_response.status_code == 201
    registration_id = reg_response.json()["id"]

    submit_response = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(event_id),
            "response_json": VALID_RESPONSE,
        },
    )
    assert submit_response.status_code == 201
    submission_id = submit_response.json()["id"]

    reg_check = await client.get(f"/registrations/{registration_id}")
    assert reg_check.json()["response_id"] == submission_id


async def test_get_form_submission_by_id(client, session_maker):
    user_id = await create_user(client, "getter@example.com")
    event_id = await create_event(session_maker, form_json=WORKSHOP_FORM)

    create_resp = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(event_id),
            "response_json": VALID_RESPONSE,
        },
    )
    submission_id = create_resp.json()["id"]

    response = await client.get(f"{BASE}{submission_id}")
    assert response.status_code == 200
    assert response.json()["id"] == submission_id


async def test_get_nonexistent_form_submission_returns_404(client):
    response = await client.get(f"{BASE}99999")
    assert response.status_code == 404


async def test_update_form_submission_revalidates(client, session_maker):
    user_id = await create_user(client, "updater@example.com")
    event_id = await create_event(session_maker, form_json=WORKSHOP_FORM)

    create_resp = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(event_id),
            "response_json": VALID_RESPONSE,
        },
    )
    submission_id = create_resp.json()["id"]

    # Valid edit bumps the response version
    edited = copy.deepcopy(VALID_RESPONSE)
    edited["answers"]["q_arrival"] = "19:00"
    response = await client.patch(f"{BASE}{submission_id}", json={"response_json": edited})
    assert response.status_code == 200
    assert response.json()["response_json"]["responseVersion"] == 2

    # Invalid edit is rejected
    broken = copy.deepcopy(VALID_RESPONSE)
    broken["answers"]["q_name"] = ""
    response = await client.patch(f"{BASE}{submission_id}", json={"response_json": broken})
    assert response.status_code == 400


async def test_delete_form_submission(client, session_maker):
    user_id = await create_user(client, "deleter@example.com")
    event_id = await create_event(session_maker, form_json=WORKSHOP_FORM)

    create_resp = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(event_id),
            "response_json": VALID_RESPONSE,
        },
    )
    submission_id = create_resp.json()["id"]

    del_resp = await client.delete(f"{BASE}{submission_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"{BASE}{submission_id}")
    assert get_resp.status_code == 404


async def test_delete_form_submission_unlinks_registration(client, session_maker):
    user_id = await create_user(client, "unlinker@example.com")
    event_id = await create_event(session_maker, form_json=WORKSHOP_FORM)

    reg_resp = await client.post(
        "/registrations/",
        json={"user_id": user_id, "event_instance_id": str(event_id), "status": "waitlist"},
    )
    registration_id = reg_resp.json()["id"]

    create_resp = await client.post(
        BASE,
        json={
            "user_id": user_id,
            "event_instance_id": str(event_id),
            "response_json": VALID_RESPONSE,
        },
    )
    submission_id = create_resp.json()["id"]

    del_resp = await client.delete(f"{BASE}{submission_id}")
    assert del_resp.status_code == 204

    reg_check = await client.get(f"/registrations/{registration_id}")
    assert reg_check.json()["response_id"] is None


async def test_get_form_submissions_filtering(client, session_maker):
    user_id1 = await create_user(client, "filter_a@example.com")
    user_id2 = await create_user(client, "filter_b@example.com")
    event_id1 = await create_event(session_maker, form_json=WORKSHOP_FORM)
    event_id2 = await create_event(session_maker, form_json=WORKSHOP_FORM)

    for user_id, event_id in [
        (user_id1, event_id1),
        (user_id1, event_id2),
        (user_id2, event_id1),
    ]:
        response = await client.post(
            BASE,
            json={
                "user_id": user_id,
                "event_instance_id": str(event_id),
                "response_json": VALID_RESPONSE,
            },
        )
        assert response.status_code == 201

    resp_user = await client.get(f"{BASE}?user_id={user_id1}")
    assert resp_user.status_code == 200
    assert len(resp_user.json()) == 2

    resp_event = await client.get(f"{BASE}?event_instance_id={event_id1}")
    assert resp_event.status_code == 200
    assert len(resp_event.json()) == 2

    resp_both = await client.get(f"{BASE}?user_id={user_id1}&event_instance_id={event_id1}")
    assert resp_both.status_code == 200
    assert len(resp_both.json()) == 1
