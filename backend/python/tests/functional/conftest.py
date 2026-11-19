import json
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import ARRAY
from sqlmodel import SQLModel

from app import create_app
from app.dependencies.auth import get_current_user, get_optional_user
from app.dependencies.services import get_storage_service
from app.models import get_session
from app.models.enum import BucketVisibility, RegistrationStatusEnum, StrikeReasonEnum, UserRole
from app.models.event import Event
from app.models.registration import Registration
from app.models.strike import Strike
from app.models.user import User

# Who every test is logged in as, unless it overrides get_current_user itself
# (see test_auth_routes.py). Admins can call every route.
FAKE_ADMIN = User(id=0, email="admin@example.com", role=UserRole.ADMIN)


class FakeStorage:
    """Stands in for R2StorageService: deterministic URLs, no boto3 / network."""

    def url_for(
        self, key: str, visibility: BucketVisibility, *, expires_in: int | None = None
    ) -> str:
        if visibility == BucketVisibility.PUBLIC:
            return f"https://public.test/{key}"
        return f"https://private.test/{key}?expires={expires_in or 3600}"


# SQLite does not natively support PostgreSQL-specific types (e.g. ARRAY, JSONB) used in models.
# These compilation overrides allow SQLite to map them to TEXT fields, preventing compilation
# errors during metadata.create_all in functional tests.
@compiles(ARRAY, "sqlite")
def compile_array_sqlite(element, compiler, **kw):
    return "TEXT"


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "TEXT"


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    from app.models import register_models

    # register_models(), not init_app(): init_app would also spin up the Postgres
    # engines and create tables there, which these SQLite-backed tests never use.
    register_models()

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = lambda: FAKE_ADMIN
    # Logged in by default, so signed (private) URLs are included in responses
    app.dependency_overrides[get_optional_user] = lambda: FAKE_ADMIN
    app.dependency_overrides[get_storage_service] = lambda: FakeStorage()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    """A session on a fresh in-memory SQLite database, for testing services directly."""
    from app.models import register_models

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    register_models()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


# Factories that insert rows through db_session. Each returns an async function.


@pytest.fixture
def make_user(db_session):
    count = 0

    async def _make(**fields) -> User:
        nonlocal count
        count += 1
        user = User(**{"email": f"user{count}@example.com", **fields})
        db_session.add(user)
        await db_session.flush()
        return user

    return _make


@pytest.fixture
def make_event(db_session):
    async def _make(start: datetime, end: datetime | None = None, **fields) -> Event:
        event = Event(
            **{
                "name": "Cleanup",
                "description": "d",
                "location": "Toronto",
                "max_attendees": 10,
                "event_status": "published",
                "headline_image_key": "event-images/cleanup.jpg",
                "start_datetime": start,
                "end_datetime": end or start + timedelta(hours=2),
                **fields,
            }
        )
        db_session.add(event)
        await db_session.flush()
        return event

    return _make


@pytest.fixture
def make_registration(db_session):
    async def _make(
        user: User,
        event: Event,
        status: RegistrationStatusEnum = RegistrationStatusEnum.ACCEPTED,
    ) -> Registration:
        assert user.id is not None
        registration = Registration(user_id=user.id, event_instance_id=event.id, status=status)
        db_session.add(registration)
        await db_session.flush()
        return registration

    return _make


@pytest.fixture
def make_strike(db_session):
    async def _make(
        user: User,
        expires_at: datetime,
        revoked_at: datetime | None = None,
        reason: StrikeReasonEnum = StrikeReasonEnum.MANUAL,
        registration: Registration | None = None,
        **fields,
    ) -> Strike:
        assert user.id is not None
        strike = Strike(
            user_id=user.id,
            reason=reason,
            expires_at=expires_at,
            revoked_at=revoked_at,
            registration_id=registration.id if registration else None,
            event_id=registration.event_instance_id if registration else None,
            **fields,
        )
        db_session.add(strike)
        await db_session.flush()
        return strike

    return _make


# SQLite's driver can't bind/read Python lists directly (unlike psycopg2's native array
# support), so ARRAY columns need explicit (de)serialization when running under sqlite.
_original_array_bind_processor = ARRAY.bind_processor
_original_array_result_processor = ARRAY.result_processor


def _array_bind_processor(self, dialect):
    if dialect.name == "sqlite":

        def process(value):
            return json.dumps(value) if value is not None else None

        return process
    return _original_array_bind_processor(self, dialect)


def _array_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":

        def process(value):
            return json.loads(value) if value is not None else None

        return process
    return _original_array_result_processor(self, dialect, coltype)


ARRAY.bind_processor = _array_bind_processor  # type: ignore[method-assign]
ARRAY.result_processor = _array_result_processor  # type: ignore[method-assign]
