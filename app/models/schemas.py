"""Request bodies that clients send to the API (validated by pydantic)."""

from pydantic import BaseModel, Field
from typing import Literal


class SetConfigRequest(BaseModel):
    """Body of POST /api/config."""

    # Which user's quota to change.
    user_id: str
    # Must be at least 1, otherwise the user could never make a request.
    limit: int = Field(gt=0)
    # Must be at least 1 second, otherwise the window would be meaningless.
    window_seconds: int = Field(gt=0)
    # Admin selects one algorithm for this user, shared by all API copies.
    algorithm: Literal["sliding_window_log", "token_bucket"] | None = None
