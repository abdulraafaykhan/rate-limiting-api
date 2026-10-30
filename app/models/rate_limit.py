"""Models describing a quota and the answer of a rate-limit check."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitConfig:
    """A user's quota: `limit` requests per `window_seconds`."""

    limit: int
    window_seconds: int
    algorithm: str | None = None


@dataclass(frozen=True)
class RateLimitResult:
    """What an algorithm tells us after checking one request."""

    # True when the request may go through.
    allowed: bool
    # The user's maximum, echoed back for the X-RateLimit-Limit header.
    limit: int
    # Requests still available right now.
    remaining: int
    # Seconds until a request would be allowed (0 when already allowed).
    retry_after_seconds: int
    window_seconds: int | None = None
    algorithm: str | None = None
    decision_at: float | None = None
