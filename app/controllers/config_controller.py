"""POST /api/config : the admin sets a user's rate limit."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies import (
    get_config_service,
    require_admin_user,
)
from app.exceptions import UserNotFound
from app.known_users import is_known_user
from app.models.rate_limit import RateLimitConfig
from app.models.schemas import SetConfigRequest
from app.models.user import User
from app.services.config_service import ConfigService
from app.views.responses import config_updated_response

router = APIRouter()


@router.post("/api/config")
async def set_config(
    body: SetConfigRequest,
    # Only an admin gets past this line; everyone else receives 403.
    admin: User = Depends(require_admin_user),
    config_service: ConfigService = Depends(get_config_service),
) -> JSONResponse:
    # Refuse to configure a user that does not exist.
    if not is_known_user(body.user_id):
        raise UserNotFound(body.user_id)

    # Save the new quota in Redis.
    new_config = RateLimitConfig(
        limit=body.limit,
        window_seconds=body.window_seconds,
        algorithm=body.algorithm,
    )
    await config_service.set_config(body.user_id, new_config)

    return config_updated_response(body.user_id, new_config)
