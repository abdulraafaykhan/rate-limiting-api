"""Every user must have a separate, independent quota."""

from tests.helpers import USER_101_HEADERS, USER_102_HEADERS


async def test_one_user_cannot_use_up_another_users_quota(client):
    # user_101 burns through their whole quota and gets blocked.
    for _ in range(6):
        await client.get("/api/data", headers=USER_101_HEADERS)
    blocked = await client.get("/api/data", headers=USER_101_HEADERS)
    assert blocked.status_code == 429

    # user_102 is not affected at all (10 per minute, none used yet).
    response = await client.get("/api/data", headers=USER_102_HEADERS)
    assert response.status_code == 200
    assert response.json()["remaining_requests"] == 9


async def test_users_have_different_limits(client):
    first = await client.get("/api/data", headers=USER_101_HEADERS)
    second = await client.get("/api/data", headers=USER_102_HEADERS)

    # user_101 has 5 per minute, user_102 has 10 per minute.
    assert first.headers["X-RateLimit-Limit"] == "5"
    assert second.headers["X-RateLimit-Limit"] == "10"
