from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.waiver_signed import WaiverSigned

OWNER_ID = 10
GUARDIAN_ID = 20
EVENT_ID = uuid4()
TEMPLATE_ID = uuid4()


def make_waiver(**overrides):
    data = {
        "user_id": OWNER_ID,
        "signed_by_user_id": GUARDIAN_ID,
        "event_id": EVENT_ID,
        "waiver_template_id": TEMPLATE_ID,
        "document_key": "waivers/10/abc.pdf",
    }
    data.update(overrides)
    return WaiverSigned(**data)


@pytest_asyncio.fixture
async def session(client, app):
    from app.models import get_session

    # Keep the generator referenced (yield, not return) so the session stays open
    session_gen = app.dependency_overrides[get_session]()
    yield await session_gen.__anext__()
    await session_gen.aclose()


@pytest_asyncio.fixture
async def signed_waiver(session):
    """A waiver for a child (id=10), signed by their guardian (user 20)"""
    session.add(User(id=GUARDIAN_ID, email="guardian@example.com"))
    session.add(User(id=OWNER_ID, email="child@example.com", guardian_id=GUARDIAN_ID))
    waiver = make_waiver()
    session.add(waiver)
    await session.commit()
    return waiver


async def test_signing_twice_for_same_event_and_template_is_rejected(session, signed_waiver):
    session.add(make_waiver(document_key="waivers/10/second.pdf"))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_same_template_can_be_signed_for_another_event(session, signed_waiver):
    session.add(make_waiver(event_id=uuid4(), document_key="waivers/10/other-event.pdf"))
    await session.commit()


def test_document_key_must_be_an_object_key():
    with pytest.raises(ValidationError):
        make_waiver(document_key="https://example.com/signed.pdf")
