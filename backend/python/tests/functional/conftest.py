import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import ARRAY
from sqlmodel import SQLModel

from app import create_app
from app.models import get_session


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

    from app.models import init_app as init_models

    # Force import of all models to register them in SQLModel metadata
    init_models()

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


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
