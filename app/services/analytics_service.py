"""Counts allowed and blocked requests per user."""

from redis.asyncio import Redis

from app.known_users import REGULAR_USER_IDS
from app.redis_keys import stats_key


class AnalyticsService:
    """Stores simple counters in Redis (HINCRBY is atomic)."""

    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client

    async def record_allowed(
        self, user_id: str, algorithm: str | None = None
    ) -> None:
        """Add one to the user's 'allowed' counter."""
        await self._record(user_id, "allowed", algorithm)

    async def record_blocked(
        self, user_id: str, algorithm: str | None = None
    ) -> None:
        """Add one to the user's 'blocked' counter."""
        await self._record(user_id, "blocked", algorithm)

    async def get_all_stats(self) -> dict[str, dict[str, int]]:
        """Return {user_id: {"allowed": n, "blocked": n}} for every user."""
        stats = {}

        for user_id in REGULAR_USER_IDS:
            saved = await self.redis_client.hgetall(stats_key(user_id))
            # Users who never called the API simply show zeros.
            stats[user_id] = {
                "allowed": int(saved.get("allowed", 0)),
                "blocked": int(saved.get("blocked", 0)),
            }

        return stats

    async def _record(self, user_id, decision, algorithm):
        # Keep lifetime totals and algorithm totals together atomically.
        async with self.redis_client.pipeline(transaction=True) as pipeline:
            pipeline.hincrby(stats_key(user_id), decision, 1)
            if algorithm:
                pipeline.hincrby(
                    stats_key(user_id), f"{algorithm}:{decision}", 1
                )
            await pipeline.execute()

    async def get_algorithm_stats(self):
        stats = {}
        for user_id in REGULAR_USER_IDS:
            saved = await self.redis_client.hgetall(stats_key(user_id))
            stats[user_id] = {
                name: {
                    decision: int(saved.get(f"{name}:{decision}", 0))
                    for decision in ("allowed", "blocked")
                }
                for name in ("sliding_window_log", "token_bucket")
            }
        return stats
