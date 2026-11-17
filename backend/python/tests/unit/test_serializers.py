from datetime import datetime
from typing import Any
from uuid import uuid4

from app.models.enum import BucketVisibility
from app.models.event import Event
from app.models.event_series import EventSeries
from app.models.event_type import EventType
from app.models.user import User
from app.models.waiver_template import WaiverTemplate
from app.serializers.event import event_read
from app.serializers.event_series import event_series_read
from app.serializers.event_type import event_type_read
from app.serializers.user import user_read
from app.serializers.waiver_template import waiver_template_read


class FakeStorage:
    def url_for(
        self, key: str, visibility: BucketVisibility, *, expires_in: int | None = None
    ) -> str:
        if visibility == BucketVisibility.PUBLIC:
            return f"https://public.test/{key}"
        return f"https://private.test/{key}?expires={expires_in or 3600}"


STORAGE = FakeStorage()


def make_event(**overrides) -> Event:
    data: dict[str, Any] = {
        "id": uuid4(),
        "name": "River Cleanup",
        "description": "d",
        "location": "Toronto",
        "max_attendees": 25,
        "event_status": "published",
        "headline_image_key": "event-images/h.jpg",
        "start_datetime": datetime(2026, 7, 15, 10),
        "end_datetime": datetime(2026, 7, 15, 12),
        "post_event_photo_keys": ["events/e1/a.jpg", "events/e1/b.jpg"],
    }
    data.update(overrides)
    return Event(**data)


def test_event_headline_is_public_and_keys_are_hidden():
    body = event_read(make_event(), STORAGE).model_dump(mode="json")
    assert body["headline_image_url"] == "https://public.test/event-images/h.jpg"
    assert not [field for field in body if field.endswith(("_key", "_keys"))]


def test_event_photos_only_with_include_photos():
    event = make_event()
    assert event_read(event, STORAGE).post_event_photo_urls == []
    assert event_read(event, STORAGE, include_photos=True).post_event_photo_urls == [
        "https://private.test/events/e1/a.jpg?expires=3600",
        "https://private.test/events/e1/b.jpg?expires=3600",
    ]


def test_event_series_and_type_headlines_are_public():
    series = EventSeries(
        recurrence="FREQ=WEEKLY",
        name="S",
        description="d",
        location="l",
        max_attendees=1,
        max_waitlist=0,
        event_status="active",
        headline_image_key="event-images/s.jpg",
        start_time=datetime(2026, 1, 1, 10).time(),
        end_time=datetime(2026, 1, 1, 12).time(),
        registration_type="lottery",
    )
    event_type = EventType(
        name="T",
        headline_image_key="event-images/t.jpg",
        description="d",
        location="l",
        max_attendees=1,
    )
    assert (
        event_series_read(series, STORAGE).headline_image_url
        == "https://public.test/event-images/s.jpg"
    )
    assert (
        event_type_read(event_type, STORAGE).headline_image_url
        == "https://public.test/event-images/t.jpg"
    )


def test_user_profile_pic_is_signed_or_none():
    with_pic = User(id=1, email="a@example.com", profile_pic_key="users/1/p.jpg")
    without = User(id=2, email="b@example.com")
    assert (
        user_read(with_pic, STORAGE).profile_pic_url
        == "https://private.test/users/1/p.jpg?expires=3600"
    )
    assert user_read(without, STORAGE).profile_pic_url is None
    assert "profile_pic_key" not in user_read(with_pic, STORAGE).model_dump()


def test_waiver_template_document_is_public():
    template = WaiverTemplate(document_key="waiver-templates/v1.pdf")
    body = waiver_template_read(template, STORAGE).model_dump()
    assert body["document_url"] == "https://public.test/waiver-templates/v1.pdf"
    assert "document_key" not in body
