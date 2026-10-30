"""Wiring: builds the services and the checks every endpoint relies on.

Controllers list what they need with `Depends(...)`; FastAPI calls the
functions below and hands the results over.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends, Header

from app.exceptions import RateLimitExceeded, TooManyActiveRequests
from app.models.rate_limit import RateLimitResult
from app.models.user import User
from app.redis_client import get_redis_client
from app.services.active_request_service import ActiveRequestService
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import authenticate, require_admin
from app.services.config_service import ConfigService
from app.services.limiter_service import LimiterService
from app.settings import settings

# ----- Service builders -----
# lru_cache makes each service a single shared object (built only once).


@lru_cache
def get_config_service() -> ConfigService:
    return ConfigService(get_redis_client(), settings)


@lru_cache
def get_limiter_service() -> LimiterService:
    return LimiterService(get_redis_client(), settings)


@lru_cache
def get_active_request_service() -> ActiveRequestService:
    return ActiveRequestService(get_redis_client(), settings)


@lru_cache
def get_analytics_service() -> AnalyticsService:
    return AnalyticsService(get_redis_client())


# ----- Request checks -----


async def authenticate_user(
    x_api_key: str | None = Header(default=None),
) -> User:
    """Identify the caller from the X-API-Key header (401 if invalid)."""
    return authenticate(x_api_key)


async def require_admin_user(
    user: User = Depends(authenticate_user),
) -> User:
    """Allow only the admin through (403 for everyone else)."""
    require_admin(user)
    return user


async def enforce_limits(
    user: User = Depends(authenticate_user),
    config_service: ConfigService = Depends(get_config_service),
    limiter_service: LimiterService = Depends(get_limiter_service),
    active_request_service: ActiveRequestService = Depends(
        get_active_request_service
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> AsyncGenerator[RateLimitResult, None]:
    """Apply both protections to a request, in this order:

    1. Active-request limit (cheap check; a refusal costs no quota).
    2. Rate limit (the quota of the user).

    Code after `yield` runs when the request is finished, which is where
    the active-request slot is given back.
    """
    # Hold an individually owned lease through work and response cleanup.
    try:
        async with active_request_service.hold(user.user_id):
            config = await config_service.get_config(user.user_id)
            result = await limiter_service.consume(user.user_id, config)
            if not result.allowed:
                await analytics_service.record_blocked(
                    user.user_id, result.algorithm
                )
                raise RateLimitExceeded(result)
            await analytics_service.record_allowed(
                user.user_id, result.algorithm
            )
            yield result
    except TooManyActiveRequests as exc:
        # Report rate quota without charging a refused active request.
        config = await config_service.get_config(user.user_id)
        exc.quota = await limiter_service.peek(user.user_id, config)
        await analytics_service.record_blocked(
            user.user_id, exc.quota.algorithm
        )
        raise
