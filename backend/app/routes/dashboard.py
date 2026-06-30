# app/routes/dashboard_routes.py
#
# Employee dashboard endpoint.
# No changes to the URL — just the response_model points to the new schema.

from fastapi import APIRouter

from app.core.dependencies import Current_User, DBSession
from app.schemas.employee.dashboard import DashboardResponse
from app.services.employee.dashboard_service import service_get_dashboard

dashboard_router = APIRouter()


@dashboard_router.get(
    "/dashboard",
    response_model=DashboardResponse,
    status_code=200,
    summary="Employee dashboard — full case overview",
    description=(
        "Returns all data needed to render the Employee Dashboard: "
        "KPI stats, case pipeline stages, action items, documents list, "
        "upcoming deadlines, payment summary, case team contacts, "
        "activity feed, and profile readiness sections."
    ),
)
async def get_dashboard(
    db: DBSession,
    current_user: Current_User,
) -> DashboardResponse:
    return await service_get_dashboard(db, current_user.user_id)