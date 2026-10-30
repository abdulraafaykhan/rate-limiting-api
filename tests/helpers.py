"""Small shared pieces so each test file stays short and readable."""

from httpx import AsyncClient

# API keys that match app/known_users.py.
USER_101_HEADERS = {"X-API-Key": "key-user-101"}
USER_102_HEADERS = {"X-API-Key": "key-user-102"}
ADMIN_HEADERS = {"X-API-Key": "admin-secret-key"}


async def set_user_limit(
    client: AsyncClient,
    user_id: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Use the admin endpoint to give a user a specific quota."""
    response = await client.post(
        "/api/config",
        json={
            "user_id": user_id,
            "limit": limit,
            "window_seconds": window_seconds,
        },
        headers=ADMIN_HEADERS,
    )
    # If this fails the whole test setup is wrong, so stop immediately.
    assert response.status_code == 200
