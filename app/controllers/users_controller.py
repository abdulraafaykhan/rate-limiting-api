"""Admin-only user metadata for the local testing dashboard."""

from fastapi import APIRouter, Depends

from app.dependencies import get_config_service, require_admin_user
from app.known_users import REGULAR_USER_IDS
from app.services.config_service import ConfigService
from app.settings import settings

router = APIRouter()


@router.get("/api/users", dependencies=[Depends(require_admin_user)])
async def list_users(service: ConfigService = Depends(get_config_service)):
    # Never return user credentials or the admin key to the browser.
    users = []
    for user_id in REGULAR_USER_IDS:
        config = await service.get_config(user_id)
        users.append(
            {
                "user_id": user_id,
                "limit": config.limit,
                "window_seconds": config.window_seconds,
                "algorithm": config.algorithm or settings.rate_limit_algorithm,
            }
        )
    return {"users": users}
