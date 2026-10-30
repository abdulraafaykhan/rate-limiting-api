"""Settings and helpers shared by the attack-simulation scripts.

Change the values below to point the scripts at your own server.
"""

import os

import httpx

# The first API copy. The second one (port 8002) is used by
# two_instances_demo.py.
BASE_URL = os.environ.get("LOADTEST_BASE_URL", "http://localhost:8001")

# Keys that match app/known_users.py.
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "admin-secret-key")
USER_API_KEYS = {
    "user_101": "key-user-101",
    "user_102": "key-user-102",
    "user_103": "key-user-103",
}


async def set_user_limit(
    client: httpx.AsyncClient,
    user_id: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Use the admin endpoint to set a quota (this also resets counters)."""
    response = await client.post(
        f"{BASE_URL}/api/config",
        json={
            "user_id": user_id,
            "limit": limit,
            "window_seconds": window_seconds,
        },
        headers={"X-API-Key": ADMIN_API_KEY},
    )
    response.raise_for_status()
