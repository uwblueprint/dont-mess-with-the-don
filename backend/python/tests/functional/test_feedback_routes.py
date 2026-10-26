import uuid

FEEDBACK_FORM = {
    "formId": "frm_event_feedback",
    "version": 1,
    "title": "Event Feedback",
    "questions": [
        {
            "id": "q_rating",
            "type": "multiple_choice",
            "label": "How was the event?",
            "required": True,
            "options": [
                {"id": "opt_great", "label": "Great"},
                {"id": "opt_okay", "label": "Okay"},
                {"id": "opt_poor", "label": "Poor"},
            ],
        },
        {"id": "q_comments", "type": "paragraph", "label": "Anything else?"},
    ],
}

REGISTRATION_FORM = {
    "formId": "frm_registration",
    "version": 1,
    "title": "Registration",
    "questions": [{"id": "q_name", "type": "short_answer", "label": "Name", "required": True}],
}


def feedback(rating: str, **extra_answers: str) -> dict:
    return {
        "formId": "frm_event_feedback",
        "formVersion": 1,
        "answers": {"q_rating": rating, **extra_answers},
    }


async def create_form(client, form_json: dict | None = None) -> str:
    response = await client.post("/forms/", json={"form_json": form_json or FEEDBACK_FORM})
    assert response.status_code == 201
    return response.json()["id"]


async def create_event(client, name: str) -> str:
    """Create an event with its own registration form"""
    response = await client.post(
        "/events",
        json={
            "name": name,
            "description": "Clean up the beach",
            "location": "Toronto",
            "max_attendees": 20,
            "event_status": "completed",
            "image": "https://example.com/beach.png",
            "start_datetime": "2026-09-15T10:00:00",
            "end_datetime": "2026-09-15T12:00:00",
            "form_json": REGISTRATION_FORM,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def create_user(client, email: str) -> int:
    response = await client.post("/users/", json={"email": email})
    assert response.status_code == 201
    return response.json()["id"]


async def submit(client, user_id: int, event_id: str, response_json, form_id: str | None = None):
    payload = {"user_id": user_id, "event_instance_id": event_id, "response_json": response_json}
    if form_id is not None:
        payload["form_id"] = form_id
    return await client.post("/form_submissions/", json=payload)


# --- Forms ---


async def test_create_and_get_form_returns_form_json(client):
    form_id = await create_form(client)

    response = await client.get(f"/forms/{form_id}")

    assert response.status_code == 200
    assert response.json()["form_json"]["formId"] == "frm_event_feedback"


async def test_create_form_with_invalid_form_json_returns_422(client):
    for bad_form in ({}, {"waiver_required": True}, {**FEEDBACK_FORM, "sections": []}):
        response = await client.post("/forms/", json={"form_json": bad_form})
        assert response.status_code == 422


async def test_update_and_delete_form(client):
    form_id = await create_form(client)

    updated = await client.patch(
        f"/forms/{form_id}", json={"form_json": {**FEEDBACK_FORM, "version": 2}}
    )
    invalid = await client.patch(f"/forms/{form_id}", json={"form_json": {}})
    deleted = await client.delete(f"/forms/{form_id}")
    missing = await client.get(f"/forms/{form_id}")

    assert updated.status_code == 200
    assert updated.json()["form_json"]["version"] == 2
    assert invalid.status_code == 422
    assert deleted.status_code == 204
    assert missing.status_code == 404


# --- Feedback submissions ---


async def test_feedback_submission_is_checked_against_its_form(client):
    form_id = await create_form(client)
    event_id = await create_event(client, "Feedback Checked")
    user_id = await create_user(client, "feedback_checked@example.com")

    # Answers the feedback form, not the event's registration form
    valid = await submit(client, user_id, event_id, feedback("opt_great"), form_id)
    bad_option = await submit(client, user_id, event_id, feedback("opt_amazing"), form_id)
    empty = await submit(client, user_id, event_id, None, form_id)
    unknown_form = await submit(client, user_id, event_id, feedback("opt_great"), str(uuid.uuid4()))

    assert valid.status_code == 201
    assert valid.json()["form_id"] == form_id
    assert bad_option.status_code == 422
    assert "invalid selection 'opt_amazing'" in bad_option.json()["detail"]
    assert empty.status_code == 422
    assert unknown_form.status_code == 422
    assert "not found" in unknown_form.json()["detail"]


async def test_update_feedback_submission_is_checked_against_its_form(client):
    form_id = await create_form(client)
    event_id = await create_event(client, "Feedback Updated")
    user_id = await create_user(client, "feedback_update@example.com")
    created = await submit(client, user_id, event_id, feedback("opt_okay"), form_id)
    url = f"/form_submissions/{created.json()['id']}"

    valid = await client.patch(url, json={"response_json": feedback("opt_poor")})
    invalid = await client.patch(url, json={"response_json": feedback("opt_amazing")})

    assert valid.status_code == 200
    assert valid.json()["response_json"]["answers"]["q_rating"] == "opt_poor"
    assert invalid.status_code == 422


# --- Event feedback endpoint ---


async def test_get_event_feedback_returns_only_that_events_feedback(client):
    form_id = await create_form(client)
    event_id = await create_event(client, "Feedback Listed")
    other_event_id = await create_event(client, "Other Event")
    alice = await create_user(client, "feedback_alice@example.com")
    bob = await create_user(client, "feedback_bob@example.com")

    registration = {"formId": "frm_registration", "formVersion": 1, "answers": {"q_name": "Al"}}
    assert (await submit(client, alice, event_id, registration)).status_code == 201
    assert (
        await submit(client, alice, event_id, feedback("opt_great"), form_id)
    ).status_code == 201
    assert (
        await submit(client, bob, event_id, feedback("opt_okay", q_comments="Too hot"), form_id)
    ).status_code == 201
    assert (
        await submit(client, bob, other_event_id, feedback("opt_poor"), form_id)
    ).status_code == 201

    response = await client.get(f"/events/{event_id}/feedback")

    assert response.status_code == 200
    ratings = sorted(item["response_json"]["answers"]["q_rating"] for item in response.json())
    assert ratings == ["opt_great", "opt_okay"]
    assert all(item["form_id"] == form_id for item in response.json())


async def test_get_event_feedback_empty_and_missing_event(client):
    event_id = await create_event(client, "No Feedback Yet")

    empty = await client.get(f"/events/{event_id}/feedback")
    missing = await client.get(f"/events/{uuid.uuid4()}/feedback")

    assert empty.status_code == 200
    assert empty.json() == []
    assert missing.status_code == 404


async def test_filter_form_submissions_by_form_id(client):
    form_id = await create_form(client)
    event_id = await create_event(client, "Feedback Filtered")
    user_id = await create_user(client, "feedback_filter@example.com")
    assert (
        await submit(client, user_id, event_id, feedback("opt_great"), form_id)
    ).status_code == 201

    response = await client.get("/form_submissions/", params={"form_id": form_id})

    assert response.status_code == 200
    assert [item["form_id"] for item in response.json()] == [form_id]
