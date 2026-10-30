"""Custom errors used across the project.

Services and dependencies raise these. `error_handlers.py` turns each one
into the right HTTP response, so business logic never builds HTTP replies.
"""

from app.models.rate_limit import RateLimitResult


class AlgorithmChanged(Exception):
    """An admin changed algorithm while a request was being dispatched."""


class AuthenticationFailed(Exception):
    """The API key is missing or unknown (HTTP 401)."""


class PermissionDenied(Exception):
    """The user is known but not allowed to do this (HTTP 403)."""


class UserNotFound(Exception):
    """The admin tried to configure a user that does not exist (404)."""

    def __init__(self, user_id: str) -> None:
        super().__init__(user_id)
        # Kept so the error response can name the missing user.
        self.user_id = user_id


class RateLimitExceeded(Exception):
    """The user has used up their quota (HTTP 429)."""

    def __init__(self, result: RateLimitResult) -> None:
        super().__init__("Rate limit exceeded")
        # Kept so the response can include limit and retry time.
        self.result = result


class TooManyActiveRequests(Exception):
    """The user has too many requests running at once (HTTP 429)."""

    def __init__(self, max_active_requests: int, retry_after: int) -> None:
        super().__init__("Too many simultaneous requests")
        # Kept so the response can tell the user the allowed maximum.
        self.max_active_requests = max_active_requests
        self.retry_after_seconds = retry_after
        self.quota: RateLimitResult | None = None
