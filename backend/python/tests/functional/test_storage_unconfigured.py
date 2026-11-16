"""Read routes must work in dev/test without any R2 settings (placeholder URLs)."""

from datetime import datetime

import pytest
import pytest_asyncio

from app.config import settings
from app.dependencies.auth import get_current_user
from app.dependencies.services import R2_REQUIRED_SETTINGS, get_storage_service
from app.models.enum import UserRole
from app.models.event import Event
from app.models.event_type import EventType
from app.models.user import User

PLACEHOLDER = "https://r2-not-configured.invalid/"


@pytest_asyncio.fixture
async def unconfigured_storage(app, client, monkeypatch):
    """Use the real get_storage_service, with every R2 setting blank"""
    from app.models import get_session

    for name in R2_REQUIRED_SETTINGS:
        monkeypatch.setattr(settings, name, "")
    app.dependency_overrides.pop(get_storage_service)
    get_storage_service.cache_clear()

    session_gen = app.dependency_overrides[get_session]()
    session = await session_gen.__anext__()
    admin = User(
        id=0, email="admin@example.com", role=UserRole.ADMIN, profile_pic_key="profile-pics/0.jpg"
    )
    session.add(admin)
    app.dependency_overrides[get_current_user] = lambda: admin
    session.add(
        EventType(
            name="Cleanup",
            headline_image_key="event-types/cleanup.jpg",
            description="d",
            location="Toronto",
            max_attendees=25,
        )
    )
    session.add(
        Event(
            name="River Cleanup",
            description="d",
            location="Toronto",
            max_attendees=25,
            event_status="published",
            headline_image_key="event-images/h.jpg",
            start_datetime=datetime(2026, 7, 15, 10),
            end_datetime=datetime(2026, 7, 15, 12),
        )
    )
    await session.commit()
    yield
    await session_gen.aclose()
    get_storage_service.cache_clear()


@pytest.mark.parametrize(
    ("path", "url_field"),
    [
        ("/events", "headline_image_url"),
        ("/event-types/", "headline_image_url"),
        ("/event-series/", None),
        ("/users/", "profile_pic_url"),
    ],
)
async def test_list_routes_return_placeholder_urls(client, unconfigured_storage, path, url_field):
    response = await client.get(path)
    assert response.status_code == 200
    if url_field:
        assert response.json()[0][url_field].startswith(PLACEHOLDER)


async def test_users_me_returns_placeholder_url(client, unconfigured_storage):
    response = await client.get("/users/me")
    assert response.status_code == 200
    assert response.json()["profile_pic_url"].startswith(PLACEHOLDER)
