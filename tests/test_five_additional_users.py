"""Exercise five extra identities together under both algorithms."""

import asyncio
from collections import Counter

import pytest

from app.settings import settings
from tests.helpers import ADMIN_HEADERS, set_user_limit

USERS = [
    (f"user_{number}", quota)
    for number, quota in zip(range(104, 109), [3, 4, 5, 7, 10])
]


@pytest.mark.parametrize("algorithm", ["sliding_window_log", "token_bucket"])
async def test_five_users_concurrency_isolation_and_analytics(
    client, monkeypatch, algorithm,
):
    monkeypatch.setattr(settings, "rate_limit_algorithm", algorithm)
    for user_id, quota in USERS:
        await set_user_limit(client, user_id, quota, 3600)

    async def exercise(user_id, quota):
        headers = {"X-API-Key": f"key-{user_id.replace('_', '-')}"}
        for _ in range(2):
            status = await client.get("/api/status", headers=headers)
            assert status.json()["remaining_requests"] == quota
        denied = await client.post(
            "/api/config", headers=headers,
            json={"user_id": "user_101", "limit": 999,
                  "window_seconds": 60},
        )
        assert denied.status_code == 403
        responses = await asyncio.gather(*[
            client.get("/api/data", headers=headers) for _ in range(100)
        ])
        assert Counter(r.status_code for r in responses) == {
            200: quota, 429: 100 - quota,
        }
        for response in responses:
            assert response.headers["X-RateLimit-Limit"] == str(quota)
            if response.status_code == 429:
                retry = response.json()["retry_after"]
                assert int(response.headers["Retry-After"]) == retry > 0
        status = await client.get("/api/status", headers=headers)
        assert status.json()["remaining_requests"] == 0
        assert status.json()["active_requests"] == 0

    results = await asyncio.gather(
        *(exercise(*user) for user in USERS), return_exceptions=True
    )
    failures = [
        result for result in results if isinstance(result, BaseException)
    ]
    assert not failures, failures
    analytics = (await client.get(
        "/api/analytics", headers=ADMIN_HEADERS
    )).json()
    for user_id, quota in USERS:
        assert analytics["users"][user_id] == {
            "allowed": quota, "blocked": 100 - quota,
        }


@pytest.mark.parametrize("algorithm", ["sliding_window_log", "token_bucket"])
async def test_five_users_recover(client, monkeypatch, algorithm):
    monkeypatch.setattr(settings, "rate_limit_algorithm", algorithm)
    for user_id, _ in USERS:
        await set_user_limit(client, user_id, 2, 2)
        headers = {"X-API-Key": f"key-{user_id.replace('_', '-')}"}
        for _ in range(2):
            reply = await client.get("/api/data", headers=headers)
            assert reply.status_code == 200
        reply = await client.get("/api/data", headers=headers)
        assert reply.status_code == 429
    await asyncio.sleep(2.2)
    for user_id, _ in USERS:
        headers = {"X-API-Key": f"key-{user_id.replace('_', '-')}"}
        reply = await client.get("/api/data", headers=headers)
        assert reply.status_code == 200
