"""GET /api/status : shows the caller's remaining quota."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies import (
    authenticate_user,
    get_active_request_service,
    get_config_service,
    get_limiter_service,
)
from app.models.user import User
from app.services.active_request_service import ActiveRequestService
from app.services.config_service import ConfigService
from app.services.limiter_service import LimiterService
from app.settings import settings
from app.views.responses import status_response

router = APIRouter()


@router.get("/api/status")
async def get_status(
    user: User = Depends(authenticate_user),
    config_service: ConfigService = Depends(get_config_service),
    limiter_service: LimiterService = Depends(get_limiter_service),
    active_request_service: ActiveRequestService = Depends(
        get_active_request_service
    ),
) -> JSONResponse:
    # Find the quota that applies to this caller.
    config = await config_service.get_config(user.user_id)

    # Peek only looks at the quota, so checking status never uses it up.
    result = await limiter_service.peek(user.user_id, config)

    # Also show how many requests the caller has running right now.
    active_requests = await active_request_service.count(user.user_id)

    return status_response(
        user=user,
        config=config,
        result=result,
        algorithm_name=result.algorithm or settings.rate_limit_algorithm,
        active_requests=active_requests,
        max_active_requests=settings.max_active_requests_per_user,
    )
