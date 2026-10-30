"""Bad or missing credentials must be rejected."""

import pytest

from tests.helpers import USER_101_HEADERS

WRONG_KEY_HEADERS = {"X-API-Key": "this-key-does-not-exist"}


@pytest.mark.parametrize("path", ["/api/data", "/api/status"])
async def test_missing_api_key_returns_401(client, path):
    response = await client.get(path)
    assert response.status_code == 401


@pytest.mark.parametrize("path", ["/api/data", "/api/status"])
async def test_wrong_api_key_returns_401(client, path):
    response = await client.get(path, headers=WRONG_KEY_HEADERS)
    assert response.status_code == 401


async def test_normal_user_cannot_change_any_quota(client):
    body = {"user_id": "user_102", "limit": 1000, "window_seconds": 60}

    # user_101 tries to raise the limit of user_102 (or their own).
    response = await client.post(
        "/api/config",
        json=body,
        headers=USER_101_HEADERS,
    )

    assert response.status_code == 403


async def test_config_without_key_returns_401(client):
    body = {"user_id": "user_101", "limit": 1000, "window_seconds": 60}

    response = await client.post("/api/config", json=body)

    assert response.status_code == 401


async def test_normal_user_cannot_read_analytics(client):
    response = await client.get("/api/analytics", headers=USER_101_HEADERS)
    assert response.status_code == 403
