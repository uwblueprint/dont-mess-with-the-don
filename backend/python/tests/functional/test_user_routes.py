from sqlalchemy.exc import IntegrityError

from app.dependencies.services import get_user_service

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


async def test_create_user_profile_pic_url_instead_of_key_returns_422(client):
    response = await client.post(
        BASE,
        json={"email": "pic@example.com", "profile_pic_key": "https://example.com/pic.jpg"},
    )
    assert response.status_code == 422


async def test_create_user_stores_profile_pic_key(client):
    response = await client.post(
        BASE, json={"email": "pic@example.com", "profile_pic_key": "users/1/abc.jpg"}
    )
    assert response.status_code == 201
    assert response.json()["profile_pic_key"] == "users/1/abc.jpg"


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


async def test_delete_user_with_signed_waivers_returns_409(app, client):
    # waiver_signed.user_id / signed_by_user_id are ON DELETE RESTRICT
    class RestrictedUserService:
        async def delete_user(self, session, user_id):
            raise IntegrityError("DELETE", {}, Exception("fk"))

    app.dependency_overrides[get_user_service] = lambda: RestrictedUserService()
    response = await client.delete(f"{BASE}1")
    assert response.status_code == 409


async def test_get_user_children_returns_200(client):
    guardian = await client.post(BASE, json={"email": "guardian@example.com"})
    guardian_id = guardian.json()["id"]

    child = await client.post(BASE, json={"email": "child@example.com", "guardian_id": guardian_id})
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
