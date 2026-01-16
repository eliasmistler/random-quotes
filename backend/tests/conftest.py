"""Pytest fixtures for API testing."""

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from fakeredis import aioredis
from httpx import ASGITransport, AsyncClient

# Placeholder for fake redis - will be set per test
_fake_redis = None


async def _get_fake_redis():
    """Return the fake redis instance."""
    global _fake_redis
    if _fake_redis is None:
        _fake_redis = aioredis.FakeRedis(decode_responses=True)
    return _fake_redis


async def _fake_check_health():
    """Fake health check that always returns True."""
    return True


async def _fake_close_pool():
    """Fake close pool that does nothing."""
    pass


# Patch at module level before importing app
patch("app.services.redis_client.get_redis", _get_fake_redis).start()
patch("app.services.redis_client.check_redis_health", _fake_check_health).start()
patch("app.services.redis_client.close_redis_pool", _fake_close_pool).start()

from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_fake_redis():
    """Reset fake redis before each test."""
    global _fake_redis
    _fake_redis = None
    yield


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
