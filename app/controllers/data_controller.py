"""GET /api/data : the sample protected endpoint."""

import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies import authenticate_user, enforce_limits
from app.models.rate_limit import RateLimitResult
from app.models.user import User
from app.settings import settings
from app.views.responses import success_response

router = APIRouter()


@router.get("/api/data")
async def get_data(
    user: User = Depends(authenticate_user),
    # enforce_limits runs before this function and may reply 429 itself.
    result: RateLimitResult = Depends(enforce_limits),
) -> JSONResponse:
    # Pretend to do slow work (0 seconds by default). Raising this lets
    # you see several requests overlap for the active-request demo.
    await asyncio.sleep(settings.simulated_work_seconds)

    return success_response(user, result)
