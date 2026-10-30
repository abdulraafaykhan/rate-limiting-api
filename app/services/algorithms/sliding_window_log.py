"""Sliding Window Log: exact counting of requests in the last N seconds."""

import uuid

from redis.asyncio import Redis

from app.exceptions import AlgorithmChanged
from app.models.rate_limit import RateLimitConfig, RateLimitResult
from app.redis_keys import config_key, rate_limit_key
from app.services.algorithms.base import RateLimitAlgorithm
from app.services.lua_loader import load_lua_script


class SlidingWindowLogAlgorithm(RateLimitAlgorithm):
    """Strict and exact; never lets a burst exceed the limit."""

    name = "sliding_window_log"

    def __init__(self, redis_client: Redis) -> None:
        super().__init__(redis_client)
        # Register the Lua script once; Redis then runs it atomically.
        self.script = redis_client.register_script(
            load_lua_script("sliding_window_log")
        )

    async def check(
        self,
        user_id: str,
        config: RateLimitConfig,
        consume: bool = True,
    ) -> RateLimitResult:
        # Each user gets their own key, so limits never mix.
        key = rate_limit_key(self.name, user_id)

        # A unique id stops two requests in the same instant from
        # overwriting each other inside the Redis sorted set.
        request_id = uuid.uuid4().hex

        # One atomic call: clean old entries, count, and maybe add.
        values = await self.script(
            keys=[key, config_key(user_id)],
            args=[
                config.limit,
                config.window_seconds,
                1 if consume else 0,
                request_id,
            ],
        )

        if values[0] == -1:
            raise AlgorithmChanged()

        return RateLimitResult(
            algorithm=self.name,
            decision_at=float(values[5]),
            allowed=bool(values[0]),
            limit=int(values[3]),
            remaining=int(values[1]),
            retry_after_seconds=int(values[2]),
            window_seconds=int(values[4]),
        )
