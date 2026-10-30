"""100 simultaneous requests must never beat the quota (Task 3)."""

import asyncio
from collections import Counter

import pytest

from app.settings import settings
from tests.helpers import USER_101_HEADERS, set_user_limit


@pytest.mark.parametrize(
    "algorithm_name",
    ["sliding_window_log", "token_bucket"],
)
async def test_exactly_ten_of_one_hundred_succeed(
    client,
    monkeypatch,
    algorithm_name,
):
    monkeypatch.setattr(settings, "rate_limit_algorithm", algorithm_name)

    # A one-hour window means (almost) nothing refills during the test.
    await set_user_limit(client, "user_101", limit=10, window_seconds=3600)

    # Fire 100 requests at the very same moment.
    responses = await asyncio.gather(
        *[
            client.get("/api/data", headers=USER_101_HEADERS)
            for _ in range(100)
        ]
    )

    # Count how many got each status code.
    status_counts = Counter(response.status_code for response in responses)

    # Exactly 10 pass and 90 are refused: no race condition.
    assert status_counts[200] == 10
    assert status_counts[429] == 90
