"""Fire 100 requests at the same moment at a user with a quota of 10.

Expected result: exactly 10 x HTTP 200 and 90 x HTTP 429.

Usage (server must be running):  python loadtest/concurrency_attack.py
"""

import asyncio
from collections import Counter

import httpx

from common import BASE_URL, USER_API_KEYS, set_user_limit

# Which user to attack.
TARGET_USER_ID = "user_101"

# The quota given to that user before the attack.
QUOTA = 10

# How many requests are sent at the same moment.
TOTAL_REQUESTS = 100

# A long window means no refill happens while the test runs.
WINDOW_SECONDS = 3600


async def main() -> None:
    # Allow all 100 connections to be open together.
    limits = httpx.Limits(max_connections=TOTAL_REQUESTS)

    async with httpx.AsyncClient(limits=limits, timeout=30) as client:
        # Reset the target to a fresh quota of 10.
        await set_user_limit(client, TARGET_USER_ID, QUOTA, WINDOW_SECONDS)

        headers = {"X-API-Key": USER_API_KEYS[TARGET_USER_ID]}

        # Send every request at once and wait for all the answers.
        responses = await asyncio.gather(
            *[
                client.get(f"{BASE_URL}/api/data", headers=headers)
                for _ in range(TOTAL_REQUESTS)
            ]
        )

    status_counts = Counter(response.status_code for response in responses)
    print(f"Sent {TOTAL_REQUESTS} requests, quota {QUOTA}")
    print(f"  HTTP 200 (allowed): {status_counts[200]}")
    print(f"  HTTP 429 (blocked): {status_counts[429]}")

    passed = status_counts == {200: QUOTA, 429: TOTAL_REQUESTS - QUOTA}
    print("RESULT:", "PASS" if passed else "FAIL (race condition!)")
    if not passed:
        raise RuntimeError(f"Unexpected response counts: {status_counts}")


if __name__ == "__main__":
    asyncio.run(main())
