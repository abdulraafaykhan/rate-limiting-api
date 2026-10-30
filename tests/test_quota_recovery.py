"""The quota must come back by itself as time passes."""

import asyncio

import pytest

from app.settings import settings
from tests.helpers import USER_101_HEADERS, set_user_limit


@pytest.mark.parametrize(
    "algorithm_name",
    ["sliding_window_log", "token_bucket"],
)
async def test_quota_recovers_after_waiting(
    client,
    monkeypatch,
    algorithm_name,
):
    # Run this test once for each algorithm.
    monkeypatch.setattr(settings, "rate_limit_algorithm", algorithm_name)

    # A tiny quota (2 requests per 2 seconds) keeps the test fast.
    await set_user_limit(client, "user_101", limit=2, window_seconds=2)

    # Use up the quota.
    for _ in range(2):
        response = await client.get("/api/data", headers=USER_101_HEADERS)
        assert response.status_code == 200

    # The next request is refused and tells us how long to wait.
    blocked = await client.get("/api/data", headers=USER_101_HEADERS)
    assert blocked.status_code == 429
    wait_seconds = blocked.json()["retry_after"]

    # Wait exactly as told (plus a small safety margin).
    await asyncio.sleep(wait_seconds + 0.2)

    # The quota has come back.
    recovered = await client.get("/api/data", headers=USER_101_HEADERS)
    assert recovered.status_code == 200
