"""Bonus 3: the analytics endpoint."""

from tests.helpers import ADMIN_HEADERS, USER_101_HEADERS


async def test_analytics_counts_allowed_and_blocked(client):
    # 7 requests against a quota of 5: 5 allowed, 2 blocked.
    for _ in range(7):
        await client.get("/api/data", headers=USER_101_HEADERS)

    response = await client.get("/api/analytics", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["users"]["user_101"] == {"allowed": 5, "blocked": 2}
    # Users who made no requests show zeros.
    assert body["users"]["user_102"] == {"allowed": 0, "blocked": 0}
    assert body["total_allowed"] == 5
    assert body["total_blocked"] == 2
