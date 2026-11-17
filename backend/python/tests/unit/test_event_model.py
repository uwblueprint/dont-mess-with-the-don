from datetime import datetime, timedelta
from uuid import uuid4

from app.models.event import Event, EventCreate, EventRead


def _event_fields() -> dict:
    return {
        "name": "River Cleanup",
        "description": "Clean up the Don Valley shoreline.",
        "location": "Toronto",
        "max_attendees": 25,
        "event_status": "published",
        "image": "https://example.com/headline.jpg",
        "start_datetime": datetime(2026, 7, 15, 10, 0, 0),
        "end_datetime": datetime(2026, 7, 15, 12, 0, 0),
    }


def test_event_gets_check_in_token_by_default() -> None:
    event = Event(**_event_fields())

    assert isinstance(event.check_in_token, str)
    assert len(event.check_in_token) >= 20


def test_each_event_gets_a_different_check_in_token() -> None:
    first = Event(**_event_fields())
    second = Event(**_event_fields())

    assert first.check_in_token != second.check_in_token


def test_recurring_instances_in_a_series_each_get_their_own_token() -> None:
    # Mirrors how the recurring job creates instances: same fields and series,
    # only the dates differ, and no token is passed in
    series_id = uuid4()
    first_start = datetime(2026, 7, 15, 10, 0, 0)
    instances = [
        Event(
            **{
                **_event_fields(),
                "event_series_id": series_id,
                "start_datetime": first_start + timedelta(weeks=week),
                "end_datetime": first_start + timedelta(weeks=week, hours=2),
            }
        )
        for week in range(10)
    ]

    tokens = [instance.check_in_token for instance in instances]
    assert all(tokens)
    assert len(set(tokens)) == len(instances)


def test_event_created_from_create_payload_gets_check_in_token() -> None:
    payload = EventCreate(**_event_fields())

    event = Event(**payload.model_dump())

    assert event.check_in_token


def test_check_in_token_is_not_exposed_on_api_models() -> None:
    assert "check_in_token" not in EventCreate.model_fields
    assert "check_in_token" not in EventRead.model_fields
