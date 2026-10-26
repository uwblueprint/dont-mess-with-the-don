import uuid

BASE = "/form_submissions/"


def make_response(tshirt_size: str) -> dict:
    return {
        "formId": "frm_beach_cleanup",
        "formVersion": 1,
        "answers": {"q_tshirt_size": tshirt_size},
    }


async def create_form_submission(client, email: str) -> dict:
    user_response = await client.post("/users/", json={"email": email})
    assert user_response.status_code == 201

    response = await client.post(
        BASE,
        json={
            "user_id": user_response.json()["id"],
            "event_instance_id": str(uuid.uuid4()),
            "response_json": make_response("opt_m"),
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_update_form_submission_returns_200(client):
    submission = await create_form_submission(client, "form_update@example.com")

    response = await client.patch(
        f"{BASE}{submission['id']}", json={"response_json": make_response("opt_l")}
    )

    assert response.status_code == 200
    assert response.json()["response_json"]["answers"] == {"q_tshirt_size": "opt_l"}


async def test_update_form_submission_with_empty_body_keeps_response(client):
    submission = await create_form_submission(client, "form_empty_patch@example.com")

    response = await client.patch(f"{BASE}{submission['id']}", json={})

    assert response.status_code == 200
    assert response.json()["response_json"]["answers"] == {"q_tshirt_size": "opt_m"}


async def test_create_form_submission_normalizes_response_json(client):
    submission = await create_form_submission(client, "form_normalize@example.com")

    assert submission["response_json"] == {**make_response("opt_m"), "responseVersion": 1}


async def test_create_form_submission_malformed_response_json_returns_422(client):
    user_response = await client.post("/users/", json={"email": "form_bad@example.com"})
    assert user_response.status_code == 201

    for bad_response in (
        {"tshirt_size": "M"},  # not shaped like a response
        {**make_response("opt_m"), "path": ["sec_intro"]},  # sections were removed
        {**make_response("opt_m"), "answers": {"q_tshirt_size": 5}},  # non-string answer
    ):
        response = await client.post(
            BASE,
            json={
                "user_id": user_response.json()["id"],
                "event_instance_id": str(uuid.uuid4()),
                "response_json": bad_response,
            },
        )
        assert response.status_code == 422


async def test_update_form_submission_malformed_response_json_returns_422(client):
    submission = await create_form_submission(client, "form_bad_patch@example.com")

    response = await client.patch(
        f"{BASE}{submission['id']}", json={"response_json": {"tshirt_size": "L"}}
    )

    assert response.status_code == 422


# --- Responses are checked against the event's form ---

TSHIRT_FORM = {
    "formId": "frm_beach_cleanup",
    "version": 1,
    "title": "Beach Cleanup Registration",
    "questions": [
        {
            "id": "q_tshirt_size",
            "type": "multiple_choice",
            "label": "T-shirt size",
            "required": True,
            "options": [{"id": "opt_m", "label": "M"}, {"id": "opt_l", "label": "L"}],
        },
        {"id": "q_notes", "type": "paragraph", "label": "Anything else?"},
    ],
}


async def create_event_with_form(client, name: str, *, on_event_type: bool = False) -> str:
    """Create an event whose form is set on the event itself or on its event type"""
    event_type_response = await client.post(
        "/event-types/",
        json={
            "name": name,
            "image": "https://example.com/beach.png",
            "description": "Clean up the beach",
            "location": "Toronto",
            "max_attendees": 20,
            "form_json": TSHIRT_FORM if on_event_type else {},
        },
    )
    assert event_type_response.status_code == 201

    event_response = await client.post(
        "/events",
        json={
            "name": name,
            "description": "Clean up the beach",
            "location": "Toronto",
            "max_attendees": 20,
            "event_status": "published",
            "event_type_id": event_type_response.json()["id"],
            "image": "https://example.com/beach.png",
            "start_datetime": "2026-11-15T10:00:00",
            "end_datetime": "2026-11-15T12:00:00",
            "form_json": None if on_event_type else TSHIRT_FORM,
        },
    )
    assert event_response.status_code == 201
    return event_response.json()["id"]


async def post_submission(client, email: str, event_id: str, response_json: dict | None):
    user_response = await client.post("/users/", json={"email": email})
    assert user_response.status_code == 201
    return await client.post(
        BASE,
        json={
            "user_id": user_response.json()["id"],
            "event_instance_id": event_id,
            "response_json": response_json,
        },
    )


async def test_create_form_submission_matching_event_form_returns_201(client):
    event_id = await create_event_with_form(client, "Matching Form")

    response = await post_submission(client, "match@example.com", event_id, make_response("opt_m"))

    assert response.status_code == 201


async def test_create_form_submission_uses_event_type_form_as_fallback(client):
    event_id = await create_event_with_form(client, "Type Form", on_event_type=True)

    valid = await post_submission(client, "type_ok@example.com", event_id, make_response("opt_l"))
    invalid = await post_submission(
        client, "type_bad@example.com", event_id, make_response("opt_xxl")
    )

    assert valid.status_code == 201
    assert invalid.status_code == 422


async def test_create_form_submission_not_matching_event_form_returns_422(client):
    event_id = await create_event_with_form(client, "Mismatched Form")
    unanswered = {**make_response("opt_m"), "answers": {"q_notes": "hello"}}
    bad_cases = {
        "invalid selection 'opt_xxl'": make_response("opt_xxl"),
        "'q_tshirt_size' is required": unanswered,
        "unknown questions": {**make_response("opt_m"), "answers": {"q_shoe_size": "9"}},
        "frm_other": {**make_response("opt_m"), "formId": "frm_other"},
        "version 2": {**make_response("opt_m"), "formVersion": 2},
        "response is required": None,
    }

    for index, (message, response_json) in enumerate(bad_cases.items()):
        response = await post_submission(
            client, f"mismatch_{index}@example.com", event_id, response_json
        )
        assert response.status_code == 422
        assert message in response.json()["detail"]

    stored = await client.get(BASE, params={"event_instance_id": event_id})
    assert stored.json() == []


async def test_update_form_submission_is_checked_against_event_form(client):
    event_id = await create_event_with_form(client, "Updated Form")
    created = await post_submission(client, "update@example.com", event_id, make_response("opt_m"))
    assert created.status_code == 201
    url = f"{BASE}{created.json()['id']}"

    invalid = await client.patch(url, json={"response_json": make_response("opt_xxl")})
    cleared = await client.patch(url, json={"response_json": None})
    untouched = await client.patch(url, json={})
    valid = await client.patch(url, json={"response_json": make_response("opt_l")})

    assert invalid.status_code == 422
    assert "invalid selection 'opt_xxl'" in invalid.json()["detail"]
    assert cleared.status_code == 422
    assert untouched.status_code == 200
    assert untouched.json()["response_json"]["answers"] == {"q_tshirt_size": "opt_m"}
    assert valid.status_code == 200
    assert valid.json()["response_json"]["answers"] == {"q_tshirt_size": "opt_l"}


async def test_form_submission_for_event_without_form_is_not_checked(client):
    event_type_response = await client.post(
        "/event-types/",
        json={
            "name": "No Form",
            "image": "https://example.com/beach.png",
            "description": "Clean up the beach",
            "location": "Toronto",
            "max_attendees": 20,
        },
    )
    event_response = await client.post(
        "/events",
        json={
            "name": "No Form",
            "description": "Clean up the beach",
            "location": "Toronto",
            "max_attendees": 20,
            "event_status": "published",
            "event_type_id": event_type_response.json()["id"],
            "image": "https://example.com/beach.png",
            "start_datetime": "2026-11-15T10:00:00",
            "end_datetime": "2026-11-15T12:00:00",
        },
    )
    assert event_response.status_code == 201

    response = await post_submission(
        client, "no_form@example.com", event_response.json()["id"], make_response("opt_m")
    )

    assert response.status_code == 201
