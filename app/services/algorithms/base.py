"""The contract every rate-limiting algorithm follows.

The rest of the app only talks to this contract, so you can swap
algorithms (or add a third one) without touching any other code.
"""

from abc import ABC, abstractmethod

from redis.asyncio import Redis

from app.models.rate_limit import RateLimitConfig, RateLimitResult
from app.redis_keys import rate_limit_key


class RateLimitAlgorithm(ABC):
    """Base class for all algorithms."""

    # Short name used in settings and inside Redis key names.
    name: str = ""

    def __init__(self, redis_client: Redis) -> None:
        # Each algorithm stores its state in Redis, never in memory.
        self.redis_client = redis_client

    @abstractmethod
    async def check(
        self,
        user_id: str,
        config: RateLimitConfig,
        consume: bool = True,
    ) -> RateLimitResult:
        """Check one request.

        consume=True counts the request (a real API call).
        consume=False only looks at the quota (used by /api/status).
        """

    async def reset(self, user_id: str) -> None:
        """Forget a user's counters so a fresh quota starts immediately."""
        await self.redis_client.delete(rate_limit_key(self.name, user_id))
