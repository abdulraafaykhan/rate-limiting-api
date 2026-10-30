"""Every Redis key name is built here, so you can find them in one place.

Putting the user id in each key gives every user their own separate data.
"""

from app.settings import settings


def config_key(user_id: str) -> str:
    """Key of the saved custom limit for one user."""
    return f"{settings.redis_key_prefix}config:{user_id}"


def rate_limit_key(algorithm_name: str, user_id: str) -> str:
    """Key of one user's counter state for one algorithm.

    The algorithm name is part of the key because each algorithm stores a
    different Redis data type (sorted set vs hash).
    """
    return f"{settings.redis_key_prefix}rate_limit:{algorithm_name}:{user_id}"


def active_requests_key(user_id: str) -> str:
    """Key of the counter of requests a user has running right now."""
    # Version the key because leases use a sorted set, not the old counter.
    return f"{settings.redis_key_prefix}active_requests:v2:{user_id}"


def stats_key(user_id: str) -> str:
    """Key of the allowed/blocked counters used by the analytics endpoint."""
    return f"{settings.redis_key_prefix}stats:{user_id}"
