"""Bonus 2: limit on simultaneous active requests."""

import asyncio
from collections import Counter

from app.settings import settings
from tests.helpers import USER_101_HEADERS, set_user_limit


async def test_only_three_requests_may_run_at_once(client, monkeypatch):
    # Allow 3 at a time, and make each request take half a second so
    # that the 10 requests below really overlap.
    monkeypatch.setattr(settings, "max_active_requests_per_user", 3)
    monkeypatch.setattr(settings, "simulated_work_seconds", 0.5)

    # A big quota proves any refusal comes from the active limit.
    await set_user_limit(client, "user_101", limit=100, window_seconds=60)

    responses = await asyncio.gather(
        *[
            client.get("/api/data", headers=USER_101_HEADERS)
            for _ in range(10)
        ]
    )

    status_counts = Counter(response.status_code for response in responses)
    assert status_counts[200] == 3
    assert status_counts[429] == 7

    # The refused ones say why.
    refused = [r for r in responses if r.status_code == 429]
    assert refused[0].json()["error"] == "Too many simultaneous requests"


async def test_slots_are_given_back_after_requests_finish(
    client,
    monkeypatch,
):
    monkeypatch.setattr(settings, "max_active_requests_per_user", 1)
    await set_user_limit(client, "user_101", limit=100, window_seconds=60)

    # Two requests one after the other never overlap, so both succeed.
    first = await client.get("/api/data", headers=USER_101_HEADERS)
    second = await client.get("/api/data", headers=USER_101_HEADERS)
    assert first.status_code == 200
    assert second.status_code == 200

    # Nothing is left running.
    status = await client.get("/api/status", headers=USER_101_HEADERS)
    assert status.json()["active_requests"] == 0
