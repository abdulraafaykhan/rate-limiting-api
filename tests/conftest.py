"""Shared test setup (fixtures) used by every test file."""

import os
from uuid import uuid4

# IMPORTANT: choose the test Redis BEFORE the app is imported, because the
# settings object reads this value the moment it is created. Database 15
# keeps tests away from your real data.
os.environ["REDIS_URL"] = os.environ.get(
    "TEST_REDIS_URL",
    "redis://localhost:6379/15",
)
os.environ["REDIS_KEY_PREFIX"] = f"tests:{uuid4().hex}:"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402
from app.redis_client import get_redis_client  # noqa: E402
from app.settings import settings  # noqa: E402


@pytest.fixture(autouse=True, params=["sliding_window_log", "token_bucket"])
async def clean_state(monkeypatch, request):
    """Give every test an empty Redis and known default settings."""
    # Delete only this run's namespace; never flush a shared database.
    async def clear_namespace():
        keys = [key async for key in get_redis_client().scan_iter(
            match=f"{settings.redis_key_prefix}*"
        )]
        if keys:
            await get_redis_client().delete(*keys)

    await clear_namespace()

    # Pin the settings the tests depend on (a local .env cannot break them).
    monkeypatch.setattr(settings, "rate_limit_algorithm", request.param)
    monkeypatch.setattr(settings, "max_active_requests_per_user", 200)
    monkeypatch.setattr(settings, "simulated_work_seconds", 0.0)

    yield
    await clear_namespace()


@pytest.fixture
async def client():
    """An HTTP client that talks to the app directly (no real server)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client
