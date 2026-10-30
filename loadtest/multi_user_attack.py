"""One noisy attacker and two well-behaved users, all at the same time.

Expected result: the attacker is blocked a lot, the others are never
blocked, because every user has an independent quota.

Usage (server must be running):  python loadtest/multi_user_attack.py
"""

import asyncio
from collections import Counter

import httpx

from common import BASE_URL, USER_API_KEYS, set_user_limit

# The attacker sends this many requests very quickly.
ATTACKER_USER_ID = "user_101"
ATTACKER_REQUESTS = 50

# The polite users send fewer requests than their quota.
POLITE_USER_IDS = ["user_102", "user_103"]
POLITE_REQUESTS = 3

# Every user gets this quota for the experiment.
QUOTA = 5
WINDOW_SECONDS = 60


async def send_requests(
    client: httpx.AsyncClient,
    user_id: str,
    total_requests: int,
) -> Counter:
    """Send requests for one user at once and count the status codes."""
    headers = {"X-API-Key": USER_API_KEYS[user_id]}
    responses = await asyncio.gather(
        *[
            client.get(f"{BASE_URL}/api/data", headers=headers)
            for _ in range(total_requests)
        ]
    )
    return Counter(response.status_code for response in responses)


async def main() -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        # Give every user the same fresh quota.
        all_user_ids = [ATTACKER_USER_ID] + POLITE_USER_IDS
        for user_id in all_user_ids:
            await set_user_limit(client, user_id, QUOTA, WINDOW_SECONDS)

        # Run the attacker and the polite users at the same time.
        attacker_counts, *polite_counts = await asyncio.gather(
            send_requests(client, ATTACKER_USER_ID, ATTACKER_REQUESTS),
            *[
                send_requests(client, user_id, POLITE_REQUESTS)
                for user_id in POLITE_USER_IDS
            ],
        )

    print(f"{ATTACKER_USER_ID} (attacker): {dict(attacker_counts)}")
    for user_id, counts in zip(POLITE_USER_IDS, polite_counts):
        print(f"{user_id} (polite):   {dict(counts)}")

    attacker_ok = attacker_counts == {
        200: QUOTA, 429: ATTACKER_REQUESTS - QUOTA,
    }
    polite_ok = all(
        counts == {200: POLITE_REQUESTS} for counts in polite_counts
    )
    print("RESULT:", "PASS" if attacker_ok and polite_ok else "FAIL")
    if not attacker_ok or not polite_ok:
        raise RuntimeError("Unexpected multi-user response counts")


if __name__ == "__main__":
    asyncio.run(main())
