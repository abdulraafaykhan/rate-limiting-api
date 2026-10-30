"""Connects each custom exception to the HTTP response it should produce."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from app.exceptions import (
    AuthenticationFailed,
    PermissionDenied,
    RateLimitExceeded,
    TooManyActiveRequests,
    UserNotFound,
)
from app.views.responses import (
    error_response,
    rate_limit_exceeded_response,
    too_many_active_requests_response,
)


async def handle_authentication_failed(
    request: Request,
    exc: AuthenticationFailed,
) -> JSONResponse:
    """401: the caller did not prove who they are."""
    return error_response(401, "Invalid or missing API key")


async def handle_permission_denied(
    request: Request,
    exc: PermissionDenied,
) -> JSONResponse:
    """403: the caller is known but not allowed."""
    return error_response(403, "Admin access required")


async def handle_user_not_found(
    request: Request,
    exc: UserNotFound,
) -> JSONResponse:
    """404: the admin named a user that does not exist."""
    return error_response(404, f"User '{exc.user_id}' not found")


async def handle_rate_limit_exceeded(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """429: out of quota."""
    return rate_limit_exceeded_response(exc.result)


async def handle_too_many_active_requests(
    request: Request,
    exc: TooManyActiveRequests,
) -> JSONResponse:
    """429: too many requests running at once."""
    return too_many_active_requests_response(
        max_active_requests=exc.max_active_requests,
        retry_after_seconds=exc.retry_after_seconds,
        quota=exc.quota,
    )


async def handle_redis_error(
    request: Request,
    exc: RedisError,
) -> JSONResponse:
    """503: Redis is down, so we cannot safely judge any request."""
    return error_response(503, "Rate limiter storage is unavailable")


def register_error_handlers(app: FastAPI) -> None:
    """Attach every handler above to the app."""
    app.add_exception_handler(
        AuthenticationFailed,
        handle_authentication_failed,
    )
    app.add_exception_handler(PermissionDenied, handle_permission_denied)
    app.add_exception_handler(UserNotFound, handle_user_not_found)
    app.add_exception_handler(RateLimitExceeded, handle_rate_limit_exceeded)
    app.add_exception_handler(
        TooManyActiveRequests,
        handle_too_many_active_requests,
    )
    app.add_exception_handler(RedisError, handle_redis_error)
