"""
lawyer_dashboard_router.py — V1 API routes for 25 - Lawyer Dashboard.

Route map (3 endpoints):

  GET /lawyer-dashboard              → Full dashboard (KPI + cases + billing)
  GET /lawyer-dashboard/recent-cases → Paginated cases for "View All" link
  GET /lawyer-dashboard/kpi-cards    → KPI cards only (lightweight poll)

Existing endpoints reused AS-IS (NOT duplicated here):
  GET /calendar/agenda     → Today's Schedule panel (left section)
  GET /calendar/deadlines  → Critical Deadlines sidebar (right section)

"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User
from app.services.attorney import lawyer_dashboard_service
from app.schemas.attorney.lawyer_dashboard import (
    DashboardKpiCards,
    LawyerDashboardResponse,
    RecentCasesResponse,
)

lawyer_dashboard_router = APIRouter()


# ===========================================================================
# A. FULL DASHBOARD — single call for entire Screen 25
# ===========================================================================

@lawyer_dashboard_router.get(
    "/lawyer-dashboard",
    response_model=LawyerDashboardResponse,
    summary="Full lawyer dashboard — 25 - Lawyer Dashboard",
)
async def get_lawyer_dashboard(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("dashboard.view_own")),
) -> LawyerDashboardResponse:
    """
    25 - Lawyer Dashboard — single aggregated call on page load.

    Returns:
    - Greeting: "Good morning, Alex!" + date
    - 4 KPI cards: Active Cases, Unbilled Hours, Deadlines Today, New Client Intakes
    - Recent Cases table (last 5 applications assigned to this attorney)
    - Monthly Billing panel: billed total, MoM %, target, progress bar, hours split

    Today's Schedule and Critical Deadlines are NOT included here.
    Frontend fetches them separately (no duplication):
      GET /api/v1/calendar/agenda     → Today's Schedule panel
      GET /api/v1/calendar/deadlines  → Critical Deadlines sidebar
    """
    return await lawyer_dashboard_service.get_dashboard(
        db, current_user.user_id
    )


# ===========================================================================
# B. KPI CARDS ONLY — lightweight poll for badge refresh
# ===========================================================================

@lawyer_dashboard_router.get(
    "/lawyer-dashboard/kpi-cards",
    response_model=DashboardKpiCards,
    summary="KPI cards only — 25 - Lawyer Dashboard lightweight refresh",
)
async def get_kpi_cards_only(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("dashboard.view_own")),
) -> DashboardKpiCards:
    """
    25 - Lawyer Dashboard — KPI cards only.
    Lighter endpoint for polling the 4 stat cards without refetching
    the full dashboard (schedule, cases, billing).
    Call every 60s if real-time badge counts are needed.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return await lawyer_dashboard_service._get_kpi_cards(
        db, current_user.user_id, now
    )


# ===========================================================================
# C. RECENT CASES — "View All" link
# ===========================================================================

@lawyer_dashboard_router.get(
    "/lawyer-dashboard/recent-cases",
    response_model=RecentCasesResponse,
    summary="Paginated recent cases — 25 - Lawyer Dashboard 'View All'",
)
async def get_recent_cases(
    limit:  int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0,  ge=0),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("dashboard.view_own")),
) -> RecentCasesResponse:
    """
    25 - Lawyer Dashboard — "View All" link next to Recent Cases table.
    Returns all applications assigned to this attorney, newest first.
    Paginated via limit/offset.
    Same row shape as the dashboard table (client, case type, status, next action).
    """
    return await lawyer_dashboard_service.get_recent_cases(
        db, current_user.user_id, limit=limit, offset=offset
    )
