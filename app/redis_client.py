"""Creates the one shared Redis connection used by the whole app."""

from redis.asyncio import BlockingConnectionPool, Redis

from app.settings import settings

# Holds the connection once it has been created (None until first use).
_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    """Return the shared Redis client, creating it on first use."""
    global _redis_client

    # Create the client only once, so every request reuses the same pool.
    if _redis_client is None:
        # decode_responses=True gives us normal strings instead of bytes.
        # Queue bursts within a bounded timeout instead of failing as soon
        # as all connections are busy. The pool remains bounded in size.
        pool = BlockingConnectionPool.from_url(
            settings.redis_url, decode_responses=True,
            max_connections=settings.redis_max_connections,
            timeout=settings.redis_pool_timeout_seconds,
            socket_timeout=settings.redis_socket_timeout_seconds,
            socket_connect_timeout=settings.redis_socket_timeout_seconds,
        )
        _redis_client = Redis(connection_pool=pool)

    return _redis_client


async def close_redis_client() -> None:
    """Close the connection pool when the app shuts down."""
    global _redis_client

    # Nothing to close if Redis was never used.
    if _redis_client is not None:
        await _redis_client.aclose(close_connection_pool=True)
        _redis_client = None
