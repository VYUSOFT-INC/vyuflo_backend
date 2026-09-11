from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Current_User
from app.core.org_scope import require_list_organization_id
from app.schemas.admin.dashboard import DashboardCountsResponse, UserLoginCardListResponse
from app.services.admin.admin_dashboard_service import get_dashboard_counts, get_recent_login_cards


admin_dashboard_router = APIRouter()


@admin_dashboard_router.get(
    "/dashboard/counts",
    response_model=DashboardCountsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard user counts",
)
async def api_get_dashboard_counts(
    current_user: Current_User,
    db: AsyncSession = Depends(get_db),
) -> DashboardCountsResponse:
    scoped_org = await require_list_organization_id(db, current_user)
    return await get_dashboard_counts(db, organization_id=scoped_org)


@admin_dashboard_router.get(
    "/dashboard/recent-logins",
    response_model=UserLoginCardListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recent login cards",
)
async def api_get_recent_logins(
    current_user: Current_User,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> UserLoginCardListResponse:
    scoped_org = await require_list_organization_id(db, current_user)
    return await get_recent_login_cards(
        db=db,
        limit=limit,
        offset=offset,
        organization_id=scoped_org,
    )
