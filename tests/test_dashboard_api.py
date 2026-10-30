"""Dashboard uses existing quota enforcement and protected admin APIs."""

import pytest

from app.dependencies import get_config_service, get_limiter_service
from tests.helpers import ADMIN_HEADERS, USER_101_HEADERS, USER_102_HEADERS


async def configure(client, user_id, algorithm, limit=2):
    reply = await client.post(
        "/api/config",
        headers=ADMIN_HEADERS,
        json={
            "user_id": user_id,
            "limit": limit,
            "window_seconds": 3600,
            "algorithm": algorithm,
        },
    )
    assert reply.status_code == 200
    assert reply.json()["algorithm"] == algorithm


async def test_user_algorithms_are_independent_and_status_is_truthful(client):
    await configure(client, "user_101", "token_bucket")
    await configure(client, "user_102", "sliding_window_log")
    first = await client.get("/api/status", headers=USER_101_HEADERS)
    second = await client.get("/api/status", headers=USER_102_HEADERS)
    assert first.json()["algorithm"] == "token_bucket"
    assert second.json()["algorithm"] == "sliding_window_log"
    for headers in (USER_101_HEADERS, USER_102_HEADERS):
        for _ in range(2):
            assert (
                await client.get("/api/data", headers=headers)
            ).status_code == 200
        assert (
            await client.get("/api/data", headers=headers)
        ).status_code == 429


async def test_switching_algorithm_resets_quota_but_preserves_analytics(
    client,
):
    for algorithm in ("token_bucket", "sliding_window_log"):
        await configure(client, "user_101", algorithm, limit=1)
        allowed = await client.get("/api/data", headers=USER_101_HEADERS)
        denied = await client.get("/api/data", headers=USER_101_HEADERS)
        assert allowed.status_code == 200 and denied.status_code == 429
        assert allowed.headers["X-RateLimit-Algorithm"] == algorithm
        assert float(allowed.headers["X-RateLimit-Timestamp"]) > 0
        assert denied.headers["Retry-After"] == str(
            denied.json()["retry_after"]
        )
    body = (await client.get("/api/analytics", headers=ADMIN_HEADERS)).json()
    assert body["users"]["user_101"] == {"allowed": 2, "blocked": 2}
    for stats in body["algorithms"]["user_101"].values():
        assert stats == {"allowed": 1, "blocked": 1}


async def test_stale_algorithm_dispatch_retries_current_config(client):
    await configure(client, "user_101", "token_bucket", limit=1)
    old = await get_config_service().get_config("user_101")
    await configure(client, "user_101", "sliding_window_log", limit=1)
    limiter = get_limiter_service()
    result = await limiter.consume("user_101", old)
    assert result.algorithm == "sliding_window_log"
    assert result.allowed
    assert not (await limiter.consume("user_101", old)).allowed


async def test_users_endpoint_requires_admin_and_never_exposes_keys(client):
    assert (await client.get("/api/users")).status_code == 401
    assert (
        await client.get("/api/users", headers=USER_101_HEADERS)
    ).status_code == 403
    response = await client.get("/api/users", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert len(response.json()["users"]) == 8
    for user in response.json()["users"]:
        assert set(user) == {"user_id", "limit", "window_seconds", "algorithm"}


async def test_algorithm_selection_is_validated_and_admin_only(client):
    body = {
        "user_id": "user_101",
        "limit": 5,
        "window_seconds": 10,
        "algorithm": "token_bucket",
    }
    assert (
        await client.post("/api/config", headers=USER_101_HEADERS, json=body)
    ).status_code == 403
    body["algorithm"] = "invalid"
    assert (
        await client.post("/api/config", headers=ADMIN_HEADERS, json=body)
    ).status_code == 422


async def test_legacy_config_uses_server_default(client):
    from app.settings import settings

    reply = await client.post(
        "/api/config",
        headers=ADMIN_HEADERS,
        json={
            "user_id": "user_101",
            "limit": 2,
            "window_seconds": 60,
        },
    )
    assert reply.status_code == 200
    assert reply.json()["algorithm"] == settings.rate_limit_algorithm
    status = await client.get("/api/status", headers=USER_101_HEADERS)
    assert status.json()["algorithm"] == settings.rate_limit_algorithm


async def test_active_blocks_are_attributed_to_selected_algorithm(
    client,
    monkeypatch,
):
    from app.dependencies import get_active_request_service
    from app.settings import settings

    await configure(client, "user_101", "token_bucket")
    monkeypatch.setattr(settings, "max_active_requests_per_user", 1)
    service = get_active_request_service()
    owner = await service.acquire("user_101")
    try:
        reply = await client.get("/api/data", headers=USER_101_HEADERS)
        assert reply.status_code == 429
        assert reply.headers["X-RateLimit-Algorithm"] == "token_bucket"
        assert reply.headers["X-RateLimit-Remaining"] == "2"
        stats = (
            await client.get("/api/analytics", headers=ADMIN_HEADERS)
        ).json()
        assert stats["algorithms"]["user_101"]["token_bucket"] == {
            "allowed": 0,
            "blocked": 1,
        }
    finally:
        await service.release("user_101", owner)
