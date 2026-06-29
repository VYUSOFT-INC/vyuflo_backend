"""
analytics_router.py — V1 API routes for Lawyer Analytics Dashboard (Screen 23).

FILE LOCATION
    app/routes/attorney/analytics.py

Route map (5 endpoints):

  GET /analytics/kpi-cards             → 5 KPI stat cards
  GET /analytics/case-status           → Case Status Breakdown chart
  GET /analytics/cases-by-visa         → Cases by Visa Type chart
  GET /analytics/caseload-over-time    → Caseload Over Time line + Case Success Rate
  GET /analytics/upcoming-actions      → Upcoming Actions Required table

All endpoints:
  • Require JWT (get_current_user)
  • Filter data to the current attorney's own cases
  • Accept period filter: this_month | q1_2026 | last_12_months | custom
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_permissions import get_current_user, get_db
from app.models.visamodels import User
from app.services.attorney import analytics_service
from app.schemas.attorney.analytics import (
    CaseloadOverTimeResponse,
    CasesByVisaResponse,
    CaseStatusResponse,
    KpiCardsResponse,
    UpcomingActionsResponse,
)

analytics_router = APIRouter(tags=["Lawyer Analytics"])


# ---------------------------------------------------------------------------
# Shared query-param docs (reused across all chart endpoints)
# ---------------------------------------------------------------------------
_PERIOD_QUERY = Query(
    default="this_month",
    description="Filter period: this_month | q1_2026 | last_12_months | custom",
)
_DATE_FROM_QUERY = Query(
    default=None,
    description="Required when period=custom. Format: YYYY-MM-DD",
)
_DATE_TO_QUERY = Query(
    default=None,
    description="Required when period=custom. Format: YYYY-MM-DD",
)


# ===========================================================================
# A. KPI CARDS
# ===========================================================================

@analytics_router.get(
    "/analytics/kpi-cards",
    response_model=KpiCardsResponse,
    summary="KPI stat cards — Active Cases, New Clients, Avg Duration, Pending Actions, Revenue",
)
async def get_kpi_cards(
    period:    str             = _PERIOD_QUERY,
    date_from: Optional[str]  = _DATE_FROM_QUERY,
    date_to:   Optional[str]  = _DATE_TO_QUERY,
    db:        AsyncSession    = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Screen 23 — powers the 5 stat cards at the top of the dashboard.

    Active Cases         — applications currently in progress / action_needed / rfe_response
    New Clients Month    — users created this calendar month with a case assigned to this attorney
    Avg Case Duration    — average days from case creation to submission (closed cases)
    Pending Actions      — open tasks across all attorney's cases
    Monthly Revenue      — null until billing module is live
    """
    return await analytics_service.get_kpi_cards(
        db, current_user.user_id, period, date_from, date_to
    )


# ===========================================================================
# B. CASE STATUS BREAKDOWN
# ===========================================================================

@analytics_router.get(
    "/analytics/case-status",
    response_model=CaseStatusResponse,
    summary="Case Status Breakdown chart data",
)
async def get_case_status_breakdown(
    period:    str             = _PERIOD_QUERY,
    date_from: Optional[str]  = _DATE_FROM_QUERY,
    date_to:   Optional[str]  = _DATE_TO_QUERY,
    db:        AsyncSession    = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Screen 23 — Case Status Breakdown section.
    Returns count + percentage per status for the attorney's cases.
    Each item includes a color_hex for the chart slice.
    """
    return await analytics_service.get_case_status_breakdown(
        db, current_user.user_id, period, date_from, date_to
    )


# ===========================================================================
# C. CASES BY VISA TYPE
# ===========================================================================

@analytics_router.get(
    "/analytics/cases-by-visa",
    response_model=CasesByVisaResponse,
    summary="Cases by Visa Type chart data",
)
async def get_cases_by_visa(
    period:    str             = _PERIOD_QUERY,
    date_from: Optional[str]  = _DATE_FROM_QUERY,
    date_to:   Optional[str]  = _DATE_TO_QUERY,
    db:        AsyncSession    = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Screen 23 — Cases by Visa Type section.
    Groups the attorney's cases by visa type code, returns count + percentage.
    """
    return await analytics_service.get_cases_by_visa(
        db, current_user.user_id, period, date_from, date_to
    )


# ===========================================================================
# D. CASELOAD OVER TIME  +  CASE SUCCESS RATE
# ===========================================================================

@analytics_router.get(
    "/analytics/caseload-over-time",
    response_model=CaseloadOverTimeResponse,
    summary="Caseload Over Time line chart + Case Success Rate card",
)
async def get_caseload_over_time(
    period:    str             = _PERIOD_QUERY,
    date_from: Optional[str]  = _DATE_FROM_QUERY,
    date_to:   Optional[str]  = _DATE_TO_QUERY,
    db:        AsyncSession    = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Screen 23 — Caseload Over Time + Case Success Rate.

    Returns monthly case counts for the selected period AND the overall
    success rate (approved / total closed × 100).
    The purple success rate card (94%) is driven by case_success_rate.
    industry_avg_rate is hardcoded at 79% — update when external benchmark data is available.
    """
    return await analytics_service.get_caseload_over_time(
        db, current_user.user_id, period, date_from, date_to
    )


# ===========================================================================
# E. UPCOMING ACTIONS TABLE
# ===========================================================================

@analytics_router.get(
    "/analytics/upcoming-actions",
    response_model=UpcomingActionsResponse,
    summary="Upcoming Actions Required table",
)
async def get_upcoming_actions(
    limit:  int        = Query(default=10, ge=1, le=100, description="Rows per page"),
    offset: int        = Query(default=0, ge=0, description="Pagination offset"),
    db:     AsyncSession = Depends(get_db),
    current_user: User   = Depends(get_current_user),
):
    """
    Screen 23 — Upcoming Actions Required table.

    Returns open tasks for the attorney's cases, ordered by due_date ASC
    (overdue tasks naturally float to the top).

    Each row contains: client name, case number + visa code,
    action title, due date, is_overdue flag, and priority label.
    """
    return await analytics_service.get_upcoming_actions(
        db, current_user.user_id, limit, offset
    )
