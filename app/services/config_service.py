"""Reads and saves each user's quota."""

from redis.asyncio import Redis

from app.known_users import STARTING_LIMITS_BY_USER
from app.models.rate_limit import RateLimitConfig
from app.redis_keys import config_key, rate_limit_key
from app.services.algorithms import ALGORITHM_CLASSES
from app.settings import Settings


class ConfigService:
    """Looks up the quota that applies to a user."""

    def __init__(self, redis_client: Redis, settings: Settings) -> None:
        self.redis_client = redis_client
        self.settings = settings

    async def get_config(self, user_id: str) -> RateLimitConfig:
        """Return the quota for a user.

        Order of priority: saved by admin -> starting limit -> default.
        """
        # 1) A limit saved by the admin wins (it lives in Redis, so it
        #    survives server restarts).
        saved = await self.redis_client.hgetall(config_key(user_id))
        if saved:
            return RateLimitConfig(
                limit=int(saved["limit"]),
                window_seconds=int(saved["window_seconds"]),
                algorithm=saved.get("algorithm") or None,
            )

        # 2) Otherwise use the starting limit from known_users.py.
        if user_id in STARTING_LIMITS_BY_USER:
            return STARTING_LIMITS_BY_USER[user_id]

        # 3) Otherwise fall back to the global default.
        return RateLimitConfig(
            limit=self.settings.default_limit,
            window_seconds=self.settings.default_window_seconds,
        )

    async def set_config(
        self,
        user_id: str,
        config: RateLimitConfig,
    ) -> None:
        """Publish the quota and reset both counters in one transaction."""
        async with self.redis_client.pipeline(transaction=True) as pipeline:
            pipeline.hset(
                config_key(user_id),
                mapping={
                    "limit": config.limit,
                    "window_seconds": config.window_seconds,
                    "algorithm": config.algorithm
                    or self.settings.rate_limit_algorithm,
                },
            )
            pipeline.delete(
                *[rate_limit_key(name, user_id) for name in ALGORITHM_CLASSES]
            )
            await pipeline.execute()
