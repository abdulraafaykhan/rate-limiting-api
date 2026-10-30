"""Bonus 1: the rate-limit headers."""

from tests.helpers import USER_101_HEADERS


async def test_success_has_limit_and_remaining_headers(client):
    response = await client.get("/api/data", headers=USER_101_HEADERS)

    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "4"
    # Retry-After only makes sense when the user is blocked.
    assert "Retry-After" not in response.headers


async def test_blocked_response_has_all_three_headers(client):
    for _ in range(5):
        await client.get("/api/data", headers=USER_101_HEADERS)

    response = await client.get("/api/data", headers=USER_101_HEADERS)

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    # The header and the JSON body must agree.
    assert response.headers["Retry-After"] == str(
        response.json()["retry_after"]
    )
