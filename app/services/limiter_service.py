"""Picks the active algorithm and runs rate-limit checks."""

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.exceptions import AlgorithmChanged
from app.models.rate_limit import RateLimitConfig, RateLimitResult
from app.services.algorithms import ALGORITHM_CLASSES
from app.services.config_service import ConfigService
from app.settings import Settings


class LimiterService:
    """The single entry point the rest of the app uses for rate limiting."""

    def __init__(self, redis_client: Redis, settings: Settings) -> None:
        self.settings = settings
        self.config_service = ConfigService(redis_client, settings)
        # Build one object per algorithm so we can switch by name.
        self.algorithms = {
            name: algorithm_class(redis_client)
            for name, algorithm_class in ALGORITHM_CLASSES.items()
        }

    def _get_active_algorithm(self, config):
        """Prefer the saved per-user algorithm to the server default."""
        name = config.algorithm or self.settings.rate_limit_algorithm

        if name not in self.algorithms:
            options = ", ".join(self.algorithms)
            raise ValueError(
                f"Unknown RATE_LIMIT_ALGORITHM '{name}'. Use: {options}"
            )

        return self.algorithms[name]

    async def consume(
        self,
        user_id: str,
        config: RateLimitConfig,
    ) -> RateLimitResult:
        """Count one real request against the user's quota."""
        return await self._check(user_id, config, consume=True)

    async def peek(
        self,
        user_id: str,
        config: RateLimitConfig,
    ) -> RateLimitResult:
        """Look at the quota without using it up."""
        return await self._check(user_id, config, consume=False)

    async def _check(self, user_id, config, consume):
        # Retry stale dispatch without charging either algorithm's quota.
        for _ in range(3):
            algorithm = self._get_active_algorithm(config)
            try:
                return await algorithm.check(user_id, config, consume)
            except AlgorithmChanged:
                config = await self.config_service.get_config(user_id)
        raise RedisError("User algorithm changed repeatedly during request")

    async def reset_user(self, user_id: str) -> None:
        """Clear a user's counters in every algorithm."""
        for algorithm in self.algorithms.values():
            await algorithm.reset(user_id)
