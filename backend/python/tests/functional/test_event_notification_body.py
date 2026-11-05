import logging
from datetime import datetime
from uuid import UUID

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.models import register_models
from app.models.event import Event, EventCreate
from app.models.event_type import EventType
from app.services.implementations.event_service import EventService

BASE = "/events"
EVENT_TYPES = "/event-types/"

TYPE_PAYLOAD = {
    "name": "Shoreline Cleanup",
    "image": "https://example.com/cleanup.png",
    "description": "Pick up trash along the river.",
    "location": "Toronto",
    "max_attendees": 20,
}


def event_payload(event_type_id, **overrides):
    data = {
        "name": "River Cleanup",
        "description": "Clean up the Don Valley shoreline.",
        "location": "Toronto",
        "max_attendees": 25,
        "event_status": "published",
        "event_type_id": event_type_id,
        "image": "https://example.com/headline.jpg",
        "start_datetime": datetime(2026, 7, 15, 10, 0, 0).isoformat(),
        "end_datetime": datetime(2026, 7, 15, 12, 0, 0).isoformat(),
        "image_urls": [],
        "notes": [],
    }
    data.update(overrides)
    return data


async def test_create_event_keeps_explicit_notification_body(client):
    event_type = await client.post(EVENT_TYPES, json=TYPE_PAYLOAD)
    event_type_id = event_type.json()["id"]

    response = await client.post(
        BASE,
        json=event_payload(event_type_id, notification_body="  Meet at the bridge.  "),
    )

    assert response.status_code == 201
    assert response.json()["notification_body"] == "Meet at the bridge."


async def test_create_event_copies_newest_body_for_same_type_only(client):
    first_type = await client.post(
        EVENT_TYPES,
        json={**TYPE_PAYLOAD, "name": "Tree Planting", "notification_body": "Type default"},
    )
    other_type = await client.post(
        EVENT_TYPES,
        json={**TYPE_PAYLOAD, "name": "Bake Sale", "notification_body": "Bring cookies."},
    )
    event_type_id = first_type.json()["id"]

    older = await client.post(
        BASE,
        json=event_payload(event_type_id, name="Planting 1", notification_body="Bring a shovel."),
    )
    newer = await client.post(
        BASE,
        json=event_payload(event_type_id, name="Planting 2", notification_body="Bring gloves."),
    )
    other = await client.post(
        BASE,
        json=event_payload(other_type.json()["id"], notification_body="Cash only."),
    )
    assert older.status_code == 201
    assert newer.status_code == 201
    assert other.status_code == 201

    copied = await client.post(BASE, json=event_payload(event_type_id, name="Planting 3"))

    assert copied.status_code == 201
    assert copied.json()["notification_body"] == "Bring gloves."


async def test_create_event_falls_back_to_event_type_body(client):
    event_type = await client.post(
        EVENT_TYPES,
        json={**TYPE_PAYLOAD, "name": "Food Drive", "notification_body": "Drop off at the hall."},
    )
    event_type_id = event_type.json()["id"]

    omitted = await client.post(BASE, json=event_payload(event_type_id, name="Drive 1"))
    explicit_null = await client.post(
        BASE,
        json=event_payload(event_type_id, name="Drive 2", notification_body=None),
    )
    spaces = await client.post(
        BASE,
        json=event_payload(event_type_id, name="Drive 3", notification_body="   "),
    )

    assert omitted.status_code == 201
    assert omitted.json()["notification_body"] == "Drop off at the hall."
    assert explicit_null.status_code == 201
    assert explicit_null.json()["notification_body"] == "Drop off at the hall."
    assert spaces.status_code == 201
    assert spaces.json()["notification_body"] == "Drop off at the hall."


async def test_create_event_without_any_body_stays_empty(client):
    event_type = await client.post(EVENT_TYPES, json={**TYPE_PAYLOAD, "name": "Quiet Walk"})
    event_type_id = event_type.json()["id"]

    omitted = await client.post(BASE, json=event_payload(event_type_id, name="Walk 1"))
    spaces = await client.post(
        BASE,
        json=event_payload(event_type_id, name="Walk 2", notification_body="   "),
    )

    assert omitted.status_code == 201
    assert omitted.json()["notification_body"] is None
    assert spaces.status_code == 201
    assert spaces.json()["notification_body"] is None


async def test_blank_body_copies_previous_message(client):
    event_type = await client.post(
        EVENT_TYPES,
        json={**TYPE_PAYLOAD, "name": "Park Day", "notification_body": "Type default"},
    )
    event_type_id = event_type.json()["id"]
    first = await client.post(
        BASE,
        json=event_payload(event_type_id, notification_body="Meet by the playground."),
    )
    assert first.status_code == 201

    explicit_null = await client.post(
        BASE,
        json=event_payload(event_type_id, name="Park Day 2", notification_body=None),
    )
    spaces = await client.post(
        BASE,
        json=event_payload(event_type_id, name="Park Day 3", notification_body="   "),
    )

    assert explicit_null.status_code == 201
    assert explicit_null.json()["notification_body"] == "Meet by the playground."
    assert spaces.status_code == 201
    assert spaces.json()["notification_body"] == "Meet by the playground."


async def test_whitespace_update_does_not_hide_previous_message(client):
    event_type = await client.post(
        EVENT_TYPES,
        json={**TYPE_PAYLOAD, "notification_body": "Type default"},
    )
    assert event_type.status_code == 201
    event_type_id = event_type.json()["id"]

    older = await client.post(
        BASE,
        json=event_payload(event_type_id, notification_body="Bring gloves."),
    )
    newer = await client.post(
        BASE,
        json=event_payload(event_type_id, notification_body="Bring a shovel."),
    )
    assert older.status_code == 201
    assert newer.status_code == 201

    updated = await client.patch(
        f"{BASE}/{newer.json()['id']}", json={"notification_body": "\n\t"}
    )
    assert updated.status_code == 200
    assert updated.json()["notification_body"] is None

    created = await client.post(BASE, json=event_payload(event_type_id))
    assert created.status_code == 201
    assert created.json()["notification_body"] == "Bring gloves."


def _event_row(event_type_id: UUID, event_id: UUID, body: str, created_at: datetime) -> Event:
    return Event(
        id=event_id,
        name="Tied event",
        description="Two events saved at the same moment.",
        location="Toronto",
        max_attendees=10,
        event_status="published",
        event_type_id=event_type_id,
        image="https://example.com/headline.jpg",
        start_datetime=datetime(2026, 7, 15, 10, 0, 0),
        end_datetime=datetime(2026, 7, 15, 12, 0, 0),
        notification_body=body,
        created_at=created_at,
    )


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    register_models()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


async def test_same_timestamp_uses_higher_id_as_tie_break(db_session):
    event_type = EventType(
        name="Tie Break",
        image="https://example.com/tie.png",
        description="Which message wins a tie.",
        location="Toronto",
        max_attendees=5,
        notification_body="Type default",
    )
    db_session.add(event_type)
    await db_session.commit()
    await db_session.refresh(event_type)

    same_time = datetime(2026, 7, 1, 12, 0, 0)
    lower_id = UUID("00000000-0000-4000-8000-000000000001")
    higher_id = UUID("ffffffff-ffff-4fff-bfff-ffffffffffff")
    db_session.add(_event_row(event_type.id, higher_id, "Later id message", same_time))
    db_session.add(_event_row(event_type.id, lower_id, "Earlier id message", same_time))
    await db_session.commit()

    created = await EventService(logging.getLogger("test")).create_event(
        db_session,
        EventCreate(
            name="Next one",
            description="Should copy the tie winner.",
            location="Toronto",
            max_attendees=5,
            event_status="published",
            event_type_id=event_type.id,
            image="https://example.com/headline.jpg",
            start_datetime=datetime(2026, 8, 1, 10, 0, 0),
            end_datetime=datetime(2026, 8, 1, 12, 0, 0),
        ),
    )

    assert created.notification_body == "Later id message"
