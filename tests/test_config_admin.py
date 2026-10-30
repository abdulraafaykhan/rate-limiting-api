"""The admin endpoint that sets quotas."""

from app.dependencies import get_config_service
from tests.helpers import ADMIN_HEADERS, USER_102_HEADERS, set_user_limit


async def test_admin_can_change_a_users_limit(client):
    await set_user_limit(client, "user_102", limit=3, window_seconds=30)

    status = await client.get("/api/status", headers=USER_102_HEADERS)

    assert status.json()["limit"] == 3
    assert status.json()["window_seconds"] == 30


async def test_new_limit_is_enforced(client):
    await set_user_limit(client, "user_102", limit=2, window_seconds=60)

    first = await client.get("/api/data", headers=USER_102_HEADERS)
    second = await client.get("/api/data", headers=USER_102_HEADERS)
    third = await client.get("/api/data", headers=USER_102_HEADERS)

    assert [first.status_code, second.status_code] == [200, 200]
    assert third.status_code == 429


async def test_limit_survives_a_service_restart(client):
    await set_user_limit(client, "user_102", limit=4, window_seconds=60)

    # Throw away the in-memory service objects, like a server restart.
    get_config_service.cache_clear()

    status = await client.get("/api/status", headers=USER_102_HEADERS)

    # The limit is read back from Redis, so it is still 4.
    assert status.json()["limit"] == 4


async def test_unknown_user_returns_404(client):
    response = await client.post(
        "/api/config",
        json={"user_id": "nobody", "limit": 5, "window_seconds": 60},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 404


async def test_invalid_limit_returns_422(client):
    response = await client.post(
        "/api/config",
        json={"user_id": "user_101", "limit": 0, "window_seconds": 60},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
