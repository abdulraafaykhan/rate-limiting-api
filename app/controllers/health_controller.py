"""GET /health : tells load balancers whether this copy is working."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.redis_client import get_redis_client
from app.settings import settings
from app.views.responses import health_response

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    # Ping Redis: if it answers, this server can do its job.
    try:
        await get_redis_client().ping()
        redis_is_up = True
    except Exception:
        # Any failure means the rate limiter cannot work right now.
        redis_is_up = False

    return health_response(redis_is_up, settings.instance_id)
