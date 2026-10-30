"""Regression checks for distributed slots, reconfiguration and failures."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import ConnectionError

from app.dependencies import (
    get_active_request_service, get_config_service, get_limiter_service,
)
from app.models.rate_limit import RateLimitConfig
from app.redis_client import get_redis_client
from app.redis_keys import config_key, rate_limit_key
from app.services.active_request_service import ActiveRequestService
from app.settings import Settings, settings
from tests.helpers import ADMIN_HEADERS, USER_101_HEADERS, set_user_limit


async def test_long_request_renews_slot_and_rejection_has_headers(
    client, monkeypatch,
):
    monkeypatch.setattr(settings, "max_active_requests_per_user", 1)
    monkeypatch.setattr(settings, "active_requests_ttl_seconds", 1)
    monkeypatch.setattr(settings, "simulated_work_seconds", 1.8)
    await set_user_limit(client, "user_101", 100, 3600)
    first = asyncio.create_task(client.get(
        "/api/data", headers=USER_101_HEADERS
    ))
    service = get_active_request_service()
    try:
        for _ in range(100):
            if await service.count("user_101") == 1:
                break
            await asyncio.sleep(0.01)
        await asyncio.sleep(1.15)
        assert not first.done()
        blocked = await client.get("/api/data", headers=USER_101_HEADERS)
        assert blocked.status_code == 429
        assert blocked.json()["error"] == "Too many simultaneous requests"
        assert blocked.headers["X-RateLimit-Limit"] == "100"
        assert blocked.headers["X-RateLimit-Remaining"] == "99"
        assert int(blocked.headers["Retry-After"]) == 1
        assert (await first).status_code == 200
        assert await service.count("user_101") == 0
        stats = (await client.get(
            "/api/analytics", headers=ADMIN_HEADERS
        )).json()["users"]["user_101"]
        assert stats == {"allowed": 1, "blocked": 1}
    finally:
        if not first.done():
            first.cancel()
        await asyncio.gather(first, return_exceptions=True)


async def test_abandoned_slot_expires_and_old_owner_cannot_release_new(
    monkeypatch,
):
    monkeypatch.setattr(settings, "max_active_requests_per_user", 1)
    monkeypatch.setattr(settings, "active_requests_ttl_seconds", 1)
    service = get_active_request_service()
    abandoned = await service.acquire("user_101")
    await asyncio.sleep(1.15)
    assert await service.count("user_101") == 0
    replacement = await service.acquire("user_101")
    await service.release("user_101", abandoned)
    assert await service.count("user_101") == 1
    await service.release("user_101", replacement)


async def test_other_instance_cannot_take_owned_slot(monkeypatch):
    from app.exceptions import TooManyActiveRequests

    monkeypatch.setattr(settings, "max_active_requests_per_user", 1)
    first = get_active_request_service()
    second = ActiveRequestService(get_redis_client(), settings)
    async with first.hold("user_101"):
        with pytest.raises(TooManyActiveRequests):
            await second.acquire("user_101")
    assert await second.count("user_101") == 0


async def test_cancelled_request_releases_owned_slot(client, monkeypatch):
    monkeypatch.setattr(settings, "simulated_work_seconds", 10)
    service = get_active_request_service()
    task = asyncio.create_task(client.get(
        "/api/data", headers=USER_101_HEADERS
    ))
    try:
        for _ in range(100):
            if await service.count("user_101") == 1:
                break
            await asyncio.sleep(0.01)
        assert await service.count("user_101") == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert await service.count("user_101") == 0


async def test_stale_config_cannot_admit_requests_after_admin_change():
    service = get_config_service()
    limiter = get_limiter_service()
    old = RateLimitConfig(1000, 3600)
    await service.set_config("user_101", old)
    # Simulate a request that read config just before the admin updated it.
    await service.set_config("user_101", RateLimitConfig(1, 60))
    accepted = await limiter.consume("user_101", old)
    denied = await limiter.consume("user_101", old)
    assert accepted.allowed and accepted.limit == 1
    assert accepted.remaining == 0 and accepted.window_seconds == 60
    assert not denied.allowed and denied.limit == 1


async def test_config_change_resets_both_algorithms():
    service = get_config_service()
    limiter = get_limiter_service()
    config = RateLimitConfig(5, 60)
    for algorithm in limiter.algorithms.values():
        await algorithm.check("user_101", config)
    await service.set_config("user_101", RateLimitConfig(3, 30))
    redis = get_redis_client()
    for name in limiter.algorithms:
        assert not await redis.exists(rate_limit_key(name, "user_101"))
    assert await redis.hget(config_key("user_101"), "limit") == "3"


async def test_storage_failure_returns_503_and_releases_slot(
    client, monkeypatch,
):
    config = get_config_service()
    monkeypatch.setattr(config, "get_config", AsyncMock(
        side_effect=ConnectionError("test storage outage")
    ))
    response = await client.get("/api/data", headers=USER_101_HEADERS)
    assert response.status_code == 503
    assert response.json() == {
        "error": "Rate limiter storage is unavailable"
    }
    assert await get_active_request_service().count("user_101") == 0


async def test_release_failure_preserves_response_and_expires(
    client, monkeypatch,
):
    service = get_active_request_service()
    monkeypatch.setattr(settings, "active_requests_ttl_seconds", 1)
    monkeypatch.setattr(service, "release", AsyncMock(
        side_effect=ConnectionError("test cleanup outage")
    ))
    response = await client.get("/api/data", headers=USER_101_HEADERS)
    assert response.status_code == 200
    await asyncio.sleep(1.15)
    assert await service.count("user_101") == 0


async def test_health_reports_unavailable_storage(client, monkeypatch):
    from app.controllers import health_controller

    unavailable = AsyncMock()
    unavailable.ping.side_effect = ConnectionError("test storage outage")
    monkeypatch.setattr(health_controller, "get_redis_client",
                        lambda: unavailable)
    response = await client.get("/health")
    assert response.status_code == 503
    assert response.json()["redis"] == "down"


async def test_user_id_header_cannot_impersonate_another_user(client):
    response = await client.get("/api/data", headers={
        **USER_101_HEADERS, "X-User-ID": "user_102",
    })
    assert response.status_code == 200
    assert response.json()["user_id"] == "user_101"


@pytest.mark.parametrize("name,value", [
    ("rate_limit_algorithm", "invalid"), ("default_limit", 0),
    ("default_window_seconds", 0), ("max_active_requests_per_user", 0),
    ("active_requests_ttl_seconds", 0), ("redis_max_connections", 0),
    ("redis_pool_timeout_seconds", 0), ("simulated_work_seconds", -1),
])
async def test_invalid_settings_fail_at_startup(name, value):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{name: value})


async def test_lease_loss_stops_work_and_releases_slot(client, monkeypatch):
    service = get_active_request_service()
    monkeypatch.setattr(settings, "active_requests_ttl_seconds", 1)
    monkeypatch.setattr(settings, "simulated_work_seconds", 2)
    monkeypatch.setattr(service, "renew", AsyncMock(return_value=False))
    response = await client.get("/api/data", headers=USER_101_HEADERS)
    assert response.status_code == 503
    assert await service.count("user_101") == 0
