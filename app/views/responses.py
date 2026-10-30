"""Every HTTP response the API sends is built in this file.

Controllers never format JSON themselves; they call a function from here.
Change a message or a field name once and it changes everywhere.
"""

from fastapi.responses import JSONResponse

from app.models.rate_limit import RateLimitConfig, RateLimitResult
from app.models.user import User
from app.settings import settings


def build_rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
    """Headers that tell the client about their quota (bonus 1)."""
    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
    }
    if result.algorithm:
        headers["X-RateLimit-Algorithm"] = result.algorithm
    if result.decision_at is not None:
        headers["X-RateLimit-Timestamp"] = str(result.decision_at)
    return headers


def success_response(user: User, result: RateLimitResult) -> JSONResponse:
    """200 reply for a request that passed the rate limit."""
    body = {
        "message": "Request successful",
        "user_id": user.user_id,
        "remaining_requests": result.remaining,
    }
    return JSONResponse(
        status_code=200,
        content=body,
        headers=build_rate_limit_headers(result),
    )


def rate_limit_exceeded_response(result: RateLimitResult) -> JSONResponse:
    """429 reply when the user has no quota left."""
    body = {
        "error": "Rate limit exceeded",
        "retry_after": result.retry_after_seconds,
    }

    # Retry-After is the standard header that tells clients how long to wait.
    headers = build_rate_limit_headers(result)
    headers["Retry-After"] = str(result.retry_after_seconds)

    return JSONResponse(status_code=429, content=body, headers=headers)


def too_many_active_requests_response(
    max_active_requests: int,
    retry_after_seconds: int,
    quota: RateLimitResult | None = None,
) -> JSONResponse:
    """429 reply when too many of the user's requests run at once."""
    body = {
        "error": "Too many simultaneous requests",
        "max_active_requests": max_active_requests,
        "retry_after": retry_after_seconds,
    }
    headers = build_rate_limit_headers(quota) if quota else {}
    headers["Retry-After"] = str(retry_after_seconds)
    return JSONResponse(
        status_code=429,
        content=body,
        headers=headers,
    )


def status_response(
    user: User,
    config: RateLimitConfig,
    result: RateLimitResult,
    algorithm_name: str,
    active_requests: int,
    max_active_requests: int,
) -> JSONResponse:
    """200 reply for GET /api/status (shows the quota, does not use it)."""
    body = {
        "user_id": user.user_id,
        "algorithm": algorithm_name,
        "limit": result.limit,
        "window_seconds": result.window_seconds or config.window_seconds,
        "remaining_requests": result.remaining,
        "retry_after": result.retry_after_seconds,
        "active_requests": active_requests,
        "max_active_requests": max_active_requests,
    }
    return JSONResponse(
        status_code=200,
        content=body,
        headers=build_rate_limit_headers(result),
    )


def config_updated_response(
    user_id: str,
    config: RateLimitConfig,
) -> JSONResponse:
    """200 reply after the admin changes a user's quota."""
    body = {
        "message": "Rate limit updated",
        "user_id": user_id,
        "limit": config.limit,
        "window_seconds": config.window_seconds,
        "algorithm": config.algorithm or settings.rate_limit_algorithm,
    }
    return JSONResponse(status_code=200, content=body)


def analytics_response(
    stats: dict[str, dict[str, int]], algorithms=None
) -> JSONResponse:
    """200 reply for GET /api/analytics."""
    # Totals across all users give a quick overall picture.
    total_allowed = sum(user["allowed"] for user in stats.values())
    total_blocked = sum(user["blocked"] for user in stats.values())

    body = {
        "users": stats,
        "total_allowed": total_allowed,
        "total_blocked": total_blocked,
        "algorithms": algorithms or {},
    }
    return JSONResponse(status_code=200, content=body)


def health_response(redis_is_up: bool, instance_id: str) -> JSONResponse:
    """Reply for GET /health (503 when Redis is unreachable)."""
    body = {
        "status": "ok" if redis_is_up else "unhealthy",
        "redis": "up" if redis_is_up else "down",
        "instance_id": instance_id,
    }
    status_code = 200 if redis_is_up else 503
    return JSONResponse(status_code=status_code, content=body)


def error_response(status_code: int, message: str) -> JSONResponse:
    """Simple {"error": "..."} reply used for 401, 403, 404 and 503."""
    return JSONResponse(status_code=status_code, content={"error": message})
