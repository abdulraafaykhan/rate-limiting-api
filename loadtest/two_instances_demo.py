"""Prove that two API copies share one limit through Redis (Task 4).

Start both copies first (see README), then run:
    python loadtest/two_instances_demo.py

Expected result: requests alternate between the copies, the first 5
succeed and the 6th is blocked no matter which copy receives it.
"""

import asyncio
import os

import httpx

from common import ADMIN_API_KEY, USER_API_KEYS

# The two running copies of the same API.
INSTANCE_URLS = os.environ.get(
    "LOADTEST_INSTANCE_URLS", "http://localhost:8001,http://localhost:8002"
).split(",")

# The user and quota used for the demo.
USER_ID = "user_101"
QUOTA = 5

# One more request than the quota, to see the block.
TOTAL_REQUESTS = QUOTA + 1


async def main() -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        # Set a fresh quota using the first copy only.
        configured = await client.post(
            f"{INSTANCE_URLS[0]}/api/config",
            json={"user_id": USER_ID, "limit": QUOTA, "window_seconds": 60},
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        configured.raise_for_status()

        headers = {"X-API-Key": USER_API_KEYS[USER_ID]}
        statuses = []
        instances = set()

        for request_number in range(TOTAL_REQUESTS):
            # Alternate: copy 1, copy 2, copy 1, copy 2 ...
            url = INSTANCE_URLS[request_number % len(INSTANCE_URLS)]
            response = await client.get(f"{url}/api/data", headers=headers)

            served_by = response.headers.get("X-Served-By", "?")
            statuses.append(response.status_code)
            instances.add(served_by)
            print(
                f"request {request_number + 1}: sent to {url} "
                f"(served by {served_by}) -> HTTP {response.status_code}"
            )

    # Only the last request should have been blocked.
    passed = (
        statuses == [200] * QUOTA + [429]
        and len(instances) == 2 and "?" not in instances
    )
    print("RESULT:", "PASS" if passed else "FAIL")
    if not passed:
        raise RuntimeError("Expected shared quota across two instances")


if __name__ == "__main__":
    asyncio.run(main())
