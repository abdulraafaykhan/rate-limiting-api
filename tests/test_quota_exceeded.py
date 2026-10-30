"""What happens when a user goes over their limit."""

from tests.helpers import USER_101_HEADERS


async def test_sixth_request_is_blocked(client):
    # Use up the whole quota of 5.
    for _ in range(5):
        response = await client.get("/api/data", headers=USER_101_HEADERS)
        assert response.status_code == 200

    # The sixth request must be refused.
    response = await client.get("/api/data", headers=USER_101_HEADERS)

    assert response.status_code == 429
    body = response.json()
    assert body["error"] == "Rate limit exceeded"
    # retry_after is calculated, so it must be between 1 and the window.
    assert 1 <= body["retry_after"] <= 60


async def test_blocked_requests_stay_blocked(client):
    for _ in range(5):
        await client.get("/api/data", headers=USER_101_HEADERS)

    # Hammering after the limit must keep returning 429.
    for _ in range(3):
        response = await client.get("/api/data", headers=USER_101_HEADERS)
        assert response.status_code == 429
