from datetime import datetime

import pytest
import pytest_asyncio

from app.models.event import Event
from app.models.waiver_template import WaiverTemplate


@pytest_asyncio.fixture
async def session(client, app):
    from app.models import get_session

    # Keep the generator referenced (yield, not return) so the session stays open
    session_gen = app.dependency_overrides[get_session]()
    yield await session_gen.__anext__()
    await session_gen.aclose()


async def test_waiver_template_cannot_be_edited(session):
    template = WaiverTemplate(document_key="waiver-templates/v1.pdf")
    session.add(template)
    await session.commit()

    template.document_key = "waiver-templates/v2.pdf"
    with pytest.raises(ValueError, match="cannot be edited"):
        await session.commit()


async def test_new_waiver_template_can_be_created(session):
    session.add(WaiverTemplate(document_key="waiver-templates/v1.pdf"))
    session.add(WaiverTemplate(document_key="waiver-templates/v2.pdf"))
    await session.commit()


async def test_event_can_switch_to_a_new_waiver_template(session):
    v1 = WaiverTemplate(document_key="waiver-templates/v1.pdf")
    v2 = WaiverTemplate(document_key="waiver-templates/v2.pdf")
    event = Event(
        name="River Cleanup",
        description="d",
        location="Toronto",
        max_attendees=25,
        event_status="published",
        headline_image_key="event-images/h.jpg",
        start_datetime=datetime(2026, 7, 15, 10),
        end_datetime=datetime(2026, 7, 15, 12),
        waiver_template_id=v1.id,
    )
    session.add_all([v1, v2, event])
    await session.commit()

    # The event's pointer changes; neither template is edited
    event.waiver_template_id = v2.id
    await session.commit()
    assert event.waiver_template_id == v2.id
