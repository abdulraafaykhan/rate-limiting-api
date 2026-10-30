"""GET /api/analytics : allowed and blocked requests per user."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies import get_analytics_service, require_admin_user
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.views.responses import analytics_response

router = APIRouter()


@router.get("/api/analytics")
async def get_analytics(
    # Admin only: normal users must not see other users' traffic.
    admin: User = Depends(require_admin_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> JSONResponse:
    stats = await analytics_service.get_all_stats()
    algorithms = await analytics_service.get_algorithm_stats()
    return analytics_response(stats, algorithms)
