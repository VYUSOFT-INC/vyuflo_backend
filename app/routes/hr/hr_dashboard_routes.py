# app/routes/hr/hr_dashboard_routes.py
#
# HR Compliance Dashboard endpoint.
#
# Mount in main.py:
#   from app.routes.hr.hr_dashboard_routes import hr_dashboard_router
#   app.include_router(hr_dashboard_router, prefix="/api/v1/employer", tags=["HR Dashboard"])
#
# NOTE on the prefix: every other HR router in this app mounts under
# /api/v1/hr/... (hr_case_router, hr_document_router, etc). This one uses
# /api/v1/employer/dashboard instead, purely to match what the frontend
# (dashboard.api.ts) already calls: axiosInstance.get('/employer/dashboard').
# Worth deciding whether to rename one side for consistency — this file
# just matches what's already there rather than picking silently.

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User
from app.schemas.hr.hr_dashboard import HRDashboardResponse
from app.services.hr.hr_dashboard_service import service_get_hr_dashboard

hr_dashboard_router = APIRouter()


@hr_dashboard_router.get(
    "/dashboard",
    response_model=HRDashboardResponse,
    status_code=200,
    summary="HR compliance dashboard — full overview",
    description=(
        "Returns everything the HR Compliance Dashboard renders: KPI stats, "
        "compliance score, expiring-visa list, recent activity, expiration "
        "timeline, and the analytics charts (visa distribution, cases by "
        "stage, monthly trend, department compliance, processing time, "
        "document completion). Scoped to cases where assigned_hr_id "
        "matches the current HR user, same scoping hr_case_service.py "
        "already uses for hr_list_cases()."
    ),
)
async def get_hr_dashboard(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
) -> HRDashboardResponse:
    return await service_get_hr_dashboard(db, current_user.user_id)