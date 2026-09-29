import uuid

BASE = "/form_submissions/"


async def create_form_submission(client, email: str) -> dict:
    user_response = await client.post("/users/", json={"email": email})
    assert user_response.status_code == 201

    response = await client.post(
        BASE,
        json={
            "user_id": user_response.json()["id"],
            "event_instance_id": str(uuid.uuid4()),
            "response_json": {"tshirt_size": "M"},
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_update_form_submission_returns_200(client):
    submission = await create_form_submission(client, "form_update@example.com")

    response = await client.patch(
        f"{BASE}{submission['id']}", json={"response_json": {"tshirt_size": "L"}}
    )

    assert response.status_code == 200
    assert response.json()["response_json"] == {"tshirt_size": "L"}


async def test_update_form_submission_with_empty_body_keeps_response(client):
    submission = await create_form_submission(client, "form_empty_patch@example.com")

    response = await client.patch(f"{BASE}{submission['id']}", json={})

    assert response.status_code == 200
    assert response.json()["response_json"] == {"tshirt_size": "M"}
