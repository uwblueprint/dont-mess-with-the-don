BASE = "/users/"


async def test_create_user_returns_201(client):
    response = await client.post(BASE, json={"email": "create@example.com"})
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "create@example.com"
    assert "id" in data


async def test_create_user_duplicate_email_returns_409(client):
    await client.post(BASE, json={"email": "dup@example.com"})
    response = await client.post(BASE, json={"email": "dup@example.com"})
    assert response.status_code == 409


async def test_create_user_invalid_profile_pic_url_returns_422(client):
    response = await client.post(
        BASE, json={"email": "pic@example.com", "profile_pic_url": "not-a-url"}
    )
    assert response.status_code == 422


async def test_get_users_returns_200(client):
    await client.post(BASE, json={"email": "list@example.com"})
    response = await client.get(BASE)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


async def test_get_user_by_id_returns_200(client):
    create = await client.post(BASE, json={"email": "fetch@example.com"})
    user_id = create.json()["id"]
    response = await client.get(f"{BASE}{user_id}")
    assert response.status_code == 200
    assert response.json()["id"] == user_id


async def test_get_nonexistent_user_returns_404(client):
    response = await client.get(f"{BASE}99999")
    assert response.status_code == 404


async def test_update_user_returns_200(client):
    create = await client.post(BASE, json={"email": "update@example.com"})
    user_id = create.json()["id"]
    response = await client.patch(f"{BASE}{user_id}", json={"region": "Toronto"})
    assert response.status_code == 200
    assert response.json()["region"] == "Toronto"


async def test_update_nonexistent_user_returns_404(client):
    response = await client.patch(f"{BASE}99999", json={"region": "Toronto"})
    assert response.status_code == 404


async def test_delete_user_returns_204(client):
    create = await client.post(BASE, json={"email": "delete@example.com"})
    user_id = create.json()["id"]
    response = await client.delete(f"{BASE}{user_id}")
    assert response.status_code == 204


async def test_delete_nonexistent_user_returns_404(client):
    response = await client.delete(f"{BASE}99999")
    assert response.status_code == 404


async def test_get_user_children_returns_200(client):
    guardian = await client.post(BASE, json={"email": "guardian@example.com"})
    guardian_id = guardian.json()["id"]

    child = await client.post(
        BASE, json={"email": "child@example.com", "guardian_id": guardian_id}
    )
    child_id = child.json()["id"]

    response = await client.get(f"{BASE}{guardian_id}/children")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == child_id


async def test_get_user_children_returns_empty_list_when_no_children(client):
    guardian = await client.post(BASE, json={"email": "lonely@example.com"})
    guardian_id = guardian.json()["id"]

    response = await client.get(f"{BASE}{guardian_id}/children")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_user_children_nonexistent_user_returns_404(client):
    response = await client.get(f"{BASE}99999/children")
    assert response.status_code == 404


async def test_response_excludes_password_hash(client):
    create_response = await client.post(
        BASE, json={"email": "secure@example.com", "password_hash": "secret"}
    )
    assert create_response.status_code == 201
    assert "password_hash" not in create_response.json()

    user_id = create_response.json()["id"]
    get_response = await client.get(f"{BASE}{user_id}")
    assert "password_hash" not in get_response.json()
