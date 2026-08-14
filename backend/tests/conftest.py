"""
Pytest configuration and global fixtures.

Provides:
- Async DB engine and session for tests (SQLite in-memory or Postgres).
- Async HTTP client (httpx) to test FastAPI routes.
- Redis mock or real client for idempotency tests.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.cache.core import redis_client
from app.database.dependencies import get_db
from app.main import app
from app.models.base import Base

# Use the real Postgres database instead of SQLite so that concurrent
# SELECT FOR UPDATE locks and greenlet async thread pools actually work!
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/wallet_db"

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)
TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def _delete_rate_limit_keys() -> None:
    async for key in redis_client.scan_iter(match="rate_limit:*"):
        await redis_client.delete(key)


@pytest_asyncio.fixture(autouse=True)
async def clear_rate_limit_keys() -> AsyncGenerator[None, None]:
    """Remove stale Redis rate-limit counters before each test."""
    await _delete_rate_limit_keys()
    yield


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database for each test.
    This creates all tables, yields the session, and drops tables afterwards.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for testing FastAPI endpoints.
    Overrides the get_db dependency to use our test session.
    """

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
