from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Project imports  (adjust paths to match your project layout)
# ---------------------------------------------------------------------------
from app.core.database import get_db                        # your AsyncSession dep
from app.core.dependencies import get_current_user
from app.schemas.admin.dashboard import DashboardCountsResponse, UserLoginCardListResponse
from app.services.admin.admin_dashboard_service import get_dashboard_counts, get_recent_login_cards   # your auth dep → UUID


admin_dashboard_router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD ROUTES
# ─────────────────────────────────────────────────────────────────────────────


@admin_dashboard_router.get(
    "/dashboard/counts",
    response_model=DashboardCountsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard user counts",
)
async def api_get_dashboard_counts(
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> DashboardCountsResponse:

    return await get_dashboard_counts(db)


@admin_dashboard_router.get(
    "/dashboard/recent-logins",
    response_model=UserLoginCardListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recent login cards",
)
async def api_get_recent_logins(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> UserLoginCardListResponse:

    return await get_recent_login_cards(
        db=db,
        limit=limit,
        offset=offset,
    )
