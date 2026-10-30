"""Every small value you may want to tweak lives in this one file.

Each setting has a default below. To change it for a test or a demo you can
either edit the default here, or set an environment variable / `.env` line
with the same name in capital letters (for example `DEFAULT_LIMIT=3`).
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings object, created once when the app starts."""

    # Also read a local `.env` file, and ignore keys we do not know about
    # (so the shared .env.example can hold extra lines such as the test URL).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ----- Redis -----
    # Where the shared rate-limit state is stored.
    redis_url: str = "redis://localhost:6379/0"
    redis_key_prefix: str = ""
    redis_max_connections: int = Field(default=100, gt=0)
    redis_pool_timeout_seconds: float = Field(default=10, gt=0)
    redis_socket_timeout_seconds: float = Field(default=5, gt=0)

    # ----- Algorithm -----
    # "sliding_window_log" (exact counting) or "token_bucket" (allows bursts).
    rate_limit_algorithm: Literal["sliding_window_log", "token_bucket"] = (
        "sliding_window_log"
    )

    # ----- Default quota -----
    # Used for any user that has no custom limit saved.
    default_limit: int = Field(default=5, gt=0)
    default_window_seconds: int = Field(default=60, gt=0)

    # ----- Admin -----
    # Whoever sends this API key is allowed to call POST /api/config.
    admin_api_key: str = "admin-secret-key"

    # ----- Active (simultaneous) request limit, bonus 2 -----
    # Kept high so it does not interfere with the 100-request concurrency
    # test. Lower it (for example to 3) to demo the feature.
    max_active_requests_per_user: int = Field(default=200, gt=0)
    # Each owned request lease is renewed while work is running.
    active_requests_ttl_seconds: int = Field(default=30, gt=0)
    # Pretend /api/data takes this long, so requests overlap in a demo.
    simulated_work_seconds: float = Field(default=0.0, ge=0)

    # ----- Instance name -----
    # Shown in the X-Served-By header to prove which copy answered.
    instance_id: str = "api-local"


# One shared settings object that the rest of the code imports.
settings = Settings()
