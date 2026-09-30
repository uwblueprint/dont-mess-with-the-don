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
