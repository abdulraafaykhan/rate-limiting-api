"""Normal requests: the happy path."""

from tests.helpers import USER_101_HEADERS


async def test_first_request_succeeds(client):
    response = await client.get("/api/data", headers=USER_101_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "message": "Request successful",
        "user_id": "user_101",
        # user_101 has 5 per minute, so 4 are left after the first one.
        "remaining_requests": 4,
    }


async def test_remaining_counts_down_to_zero(client):
    remaining_values = []

    # user_101 may make exactly 5 requests per minute.
    for _ in range(5):
        response = await client.get("/api/data", headers=USER_101_HEADERS)
        assert response.status_code == 200
        remaining_values.append(response.json()["remaining_requests"])

    assert remaining_values == [4, 3, 2, 1, 0]


async def test_status_does_not_use_up_quota(client):
    # Checking the status many times must not cost any requests.
    for _ in range(10):
        status = await client.get("/api/status", headers=USER_101_HEADERS)
        assert status.status_code == 200
        assert status.json()["remaining_requests"] == 5

    # The full quota is still there for real requests.
    response = await client.get("/api/data", headers=USER_101_HEADERS)
    assert response.json()["remaining_requests"] == 4


async def test_health_needs_no_api_key(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["redis"] == "up"
