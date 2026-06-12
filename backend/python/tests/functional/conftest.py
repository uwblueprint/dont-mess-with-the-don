import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import create_app
from app.models import get_session
from app.models.user import User


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Only create the users table — other models use PostgreSQL-only types (e.g. ARRAY)
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()
