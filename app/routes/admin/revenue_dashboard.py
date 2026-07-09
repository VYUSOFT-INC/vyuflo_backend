"""
app/api/v1/revenue_dashboard.py

NEW FILE — ADMIN-08 Revenue Dashboard router.

MOUNT IN main.py — add these 3 lines:

    from app.api.v1.revenue_dashboard import revenue_dashboard_router
    app.include_router(
        revenue_dashboard_router,
        prefix="/api/v1",
        tags=["Admin — Revenue Dashboard"]
    )

INTERLINK WITH EXISTING FILES:
  - Uses same DBSession, Current_User, PermissionChecker as subscription.py router
  - Uses same _admin_only / _view_billing pattern as subscription.py
  - Imports schemas from app.schemas.revenue_dashboard (NEW file)
  - Imports services from app.services.revenue_dashboard_service (NEW file)
  - Does NOT modify subscription.py router in any way

PERMISSION USED:
  - "subscriptions.manage" — already exists in your RBAC system (same as subscription.py)
  - "subscriptions.view"   — already exists (same read-only guard)
  No new permissions needed.

ENDPOINT MAP → UI COMPONENT:
  GET  /admin/revenue/dashboard/full    → Entire ADMIN-08 page (one call)
  GET  /admin/revenue/dashboard         → 4 KPI cards + failing banner
  GET  /admin/revenue/trend             → Revenue Trend line chart
  GET  /admin/revenue/plan-distribution → Plan Distribution donut
  GET  /admin/revenue/transactions      → Recent Transactions table
  GET  /admin/revenue/trial-conversions → Trial Conversions bar chart
  GET  /admin/revenue/failing-payments  → Failing Payments detail (Review button)
  GET  /admin/revenue/export            → Export Report button (CSV download)
  POST /admin/revenue/targets           → Admin sets monthly MRR target
  GET  /admin/revenue/targets           → Fetch targets for trend chart

ROUTE ORDER NOTE:
  /dashboard/full and /dashboard/export and /dashboard/failing-payments
  are all declared BEFORE /{dynamic} patterns to avoid FastAPI path collisions.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import Current_User, DBSession
from app.core.core_permissions import PermissionChecker

# ── Schema imports ─────────────────────────────────────────────────────────────
from app.schemas.admin.revenue_dashboard import (
    DateRangeFilter,
    ExportReportRequest,
    FailingPaymentsDetailResponse,
    PlanDistributionResponse,
    RecentTransactionsResponse,
    RevenueDashboardFullResponse,
    RevenueDashboardKPIResponse,
    RevenueTrendResponse,
    RevenueTargetCreate,
    RevenueTargetListResponse,
    RevenueTargetResponse,
    TrialConversionsResponse,
)

# ── Service imports ─────────────────────────────────────────────────────────────
from app.services.admin.revenue_dashboard_service import (
    _build_target_response,
    service_create_or_update_target,
    service_export_revenue_report,
    service_get_failing_payments,
    service_get_full_dashboard,
    service_get_plan_distribution,
    service_get_recent_transactions,
    service_get_revenue_kpis,
    service_get_revenue_trend,
    service_get_trial_conversions,
    service_list_targets,
)

revenue_dashboard_router = APIRouter()

# ── Permission guards (same names as subscription.py — no new permissions needed)
_admin_only   = PermissionChecker("subscriptions.manage")
_view_billing = PermissionChecker(["subscriptions.manage", "subscriptions.view"])


# =============================================================================
# ── FULL DASHBOARD (single call — reduces waterfall on page load)
# GET /admin/revenue/dashboard/full
# MUST be declared BEFORE /admin/revenue/dashboard (path prefix match)
# =============================================================================

@revenue_dashboard_router.get(
    "/admin/revenue/dashboard/full",
    response_model=RevenueDashboardFullResponse,
    status_code=status.HTTP_200_OK,
    summary="Full ADMIN-08 Revenue Dashboard — all sections in one call",
    description=(
        "Returns KPI cards + failing banner + revenue trend + plan distribution "
        "+ recent transactions + trial conversions in a single response. "
        "Use this for the initial page load to avoid 5 waterfall requests. "
        "Frontend can also call individual endpoints for selective refresh."
    ),
)
async def get_full_dashboard(
    db:     DBSession,
    _:      Current_User = _view_billing,
    period: str = Query(
        "last_12_months",
        description="this_month | last_12_months | quarter | custom",
    ),
) -> RevenueDashboardFullResponse:
    return await service_get_full_dashboard(db, period=period)


# =============================================================================
# ── KPI CARDS + FAILING PAYMENTS BANNER
# GET /admin/revenue/dashboard
# Powers: 4 KPI cards + alert banner at top of ADMIN-08
# =============================================================================

@revenue_dashboard_router.get(
    "/admin/revenue/dashboard",
    response_model=RevenueDashboardKPIResponse,
    status_code=status.HTTP_200_OK,
    summary="Revenue Dashboard KPI cards + failing payments alert",
    description=(
        "Returns all 4 KPI cards and the failing payments banner. "
        "KPI Cards: MRR ($124.5K +12.5%), ARR ($1.49M +8.2%), "
        "Active Subscribers (2,845 +156), Net Revenue Churn (1.2% ▼0.3%). "
        "Failing Payments: count + MRR at risk + breakdown by failure code. "
        "Reads from revenue_snapshots for speed; falls back to live OLTP query "
        "if no snapshot exists (testing mode). "
        "Recommend 60s cache in production."
    ),
)
async def get_revenue_kpis(
    db:        DBSession,
    _:         Current_User = _view_billing,
    period:    str           = Query("last_12_months",
                                     description="this_month | last_12_months | quarter | custom"),
    date_from: Optional[str] = Query(None, description="ISO date: 2026-01-01. Required when period=custom"),
    date_to:   Optional[str] = Query(None, description="ISO date: 2026-12-31. Required when period=custom"),
) -> RevenueDashboardKPIResponse:
    from datetime import date
    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to)   if date_to   else None
    return await service_get_revenue_kpis(db, period=period, date_from=df, date_to=dt)


# =============================================================================
# ── REVENUE TREND CHART
# GET /admin/revenue/trend
# Powers: Revenue Trend line chart (MRR actual + Target dashed line)
# =============================================================================

@revenue_dashboard_router.get(
    "/admin/revenue/trend",
    response_model=RevenueTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Revenue Trend chart data — monthly MRR + target line",
    description=(
        "Returns monthly MRR data points for the Revenue Trend line chart. "
        "Each data point includes actual MRR and optional target MRR (admin-set). "
        "Frontend renders: solid blue MRR line + dashed grey Target line. "
        "Y-axis bounds are pre-computed (y_axis_max_cents, y_axis_step_cents)."
    ),
)
async def get_revenue_trend(
    db:             DBSession,
    _:              Current_User = _view_billing,
    period_months:  int          = Query(12, ge=1, le=24,
                                         description="Number of months. 12=last 12 months. Max 24."),
    period:         str          = Query("last_12_months",
                                         description="this_month | last_12_months | quarter | custom"),
    date_from:      Optional[str] = Query(None),
    date_to:        Optional[str] = Query(None),
) -> RevenueTrendResponse:
    from datetime import date
    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to)   if date_to   else None
    return await service_get_revenue_trend(
        db, period_months=period_months, period=period, date_from=df, date_to=dt
    )


# =============================================================================
# ── PLAN DISTRIBUTION DONUT
# GET /admin/revenue/plan-distribution
# Powers: Plan Distribution donut chart (Enterprise 45% / Pro 35% / Starter 20%)
# =============================================================================

@revenue_dashboard_router.get(
    "/admin/revenue/plan-distribution",
    response_model=PlanDistributionResponse,
    status_code=status.HTTP_200_OK,
    summary="Plan Distribution donut chart data",
    description=(
        "Returns MRR breakdown by plan for the donut chart. "
        "Each slice includes: plan_name, mrr_cents, mrr_display, percentage, color. "
        "Center of donut shows total_mrr_display = '$124.5K'. "
        "Legend: Enterprise 45% / Professional 35% / Starter 20%."
    ),
)
async def get_plan_distribution(
    db: DBSession,
    _:  Current_User = _view_billing,
) -> PlanDistributionResponse:
    return await service_get_plan_distribution(db)


# =============================================================================
# ── RECENT TRANSACTIONS TABLE
# GET /admin/revenue/transactions
# Powers: Recent Transactions table at bottom-left of ADMIN-08
# Also used by "View All" link (higher page_size or pagination)
# =============================================================================

@revenue_dashboard_router.get(
    "/admin/revenue/transactions",
    response_model=RecentTransactionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Recent Transactions table",
    description=(
        "Returns paginated billing transactions. "
        "Dashboard shows the latest 4 rows. "
        "'View All' uses pagination (page=2, page_size=20). "
        "Each row: avatar initials, customer name + email, amount, plan, date, status badge. "
        "Status values: Success (green) | Failed (red) | Pending (yellow) | Refunded (gray). "
        "Filter by status to show only Failed for the Failing Payments workflow."
    ),
)
async def get_recent_transactions(
    db:            DBSession,
    _:             Current_User = _view_billing,
    page:          int           = Query(1,  ge=1),
    page_size:     int           = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(
        None, alias="status",
        description="paid | failed | pending | open | refunded | void"
    ),
    date_from:     Optional[str] = Query(None, description="ISO date: 2026-01-01"),
    date_to:       Optional[str] = Query(None, description="ISO date: 2026-12-31"),
) -> RecentTransactionsResponse:
    from datetime import date
    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to)   if date_to   else None
    return await service_get_recent_transactions(
        db,
        page          = page,
        page_size     = page_size,
        status_filter = status_filter,
        date_from     = df,
        date_to       = dt,
    )


# =============================================================================
# ── TRIAL CONVERSIONS BAR CHART
# GET /admin/revenue/trial-conversions
# Powers: Trial Conversions bar chart (Conversion vs Churn over 6 months)
# =============================================================================

@revenue_dashboard_router.get(
    "/admin/revenue/trial-conversions",
    response_model=TrialConversionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Trial Conversions bar chart data",
    description=(
        "Returns monthly trial vs conversion data for the bar chart. "
        "X-axis: last N months (default 6: May Jun Jul Aug Sep Oct). "
        "Y-axis: counts (0 / 50 / 100 / 150). "
        "Each month: new_trials (total bar height), converted_trials (solid), "
        "churned_trials (lighter). "
        "Also returns avg_conversion_rate_pct for the period summary."
    ),
)
async def get_trial_conversions(
    db:             DBSession,
    _:              Current_User = _view_billing,
    period_months:  int          = Query(6, ge=1, le=12,
                                         description="Number of months for bar chart. Default 6."),
) -> TrialConversionsResponse:
    return await service_get_trial_conversions(db, period_months=period_months)


# =============================================================================
# ── FAILING PAYMENTS DETAIL
# GET /admin/revenue/failing-payments
# MUST be declared BEFORE /admin/revenue/{dynamic} if any dynamic routes exist
# Powers: "Review Failing Payments" button → detail modal/list
# =============================================================================

@revenue_dashboard_router.get(
    "/admin/revenue/failing-payments",
    response_model=FailingPaymentsDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Failing Payments detail list",
    description=(
        "Returns full list of invoices with status='failed'. "
        "Triggered by 'Review Failing Payments' button on the banner. "
        "Each row: customer, amount, plan, attempt_count, next retry time, "
        "failure reason (expired card / insufficient funds), MRR at risk. "
        "Admin can use stripe_invoice_id to action directly in Stripe dashboard."
    ),
)
async def get_failing_payments(
    db:        DBSession,
    _:         Current_User = _view_billing,
    page:      int           = Query(1,  ge=1),
    page_size: int           = Query(20, ge=1, le=100),
) -> FailingPaymentsDetailResponse:
    return await service_get_failing_payments(db, page=page, page_size=page_size)


# =============================================================================
# ── EXPORT REPORT (CSV)
# GET /admin/revenue/export
# MUST be declared BEFORE any /{id} dynamic routes
# Powers: "Export Report" button in the page header
# =============================================================================

@revenue_dashboard_router.get(
    "/admin/revenue/export",
    status_code=status.HTTP_200_OK,
    summary="Export Revenue Report as CSV",
    description=(
        "Downloads a CSV file with KPI summary, plan breakdown, and transactions. "
        "Triggered by 'Export Report' button in the header. "
        "Content-Disposition: attachment; filename=revenue_report_{date}.csv"
    ),
)
async def export_revenue_report(
    db:                     DBSession,
    _:                      Current_User = _admin_only,
    period:                 str          = Query("last_12_months"),
    date_from:              Optional[str] = Query(None),
    date_to:                Optional[str] = Query(None),
    include_transactions:   bool          = Query(True),
    include_kpi_summary:    bool          = Query(True),
    include_plan_breakdown: bool          = Query(True),
) -> StreamingResponse:
    from datetime import date, datetime, timezone
    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to)   if date_to   else None

    csv_content = await service_export_revenue_report(
        db,
        period                 = period,
        date_from              = df,
        date_to                = dt,
        include_transactions   = include_transactions,
        include_kpi_summary    = include_kpi_summary,
        include_plan_breakdown = include_plan_breakdown,
    )

    filename = f"revenue_report_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"

    def _iter():
        yield csv_content

    return StreamingResponse(
        _iter(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# =============================================================================
# ── REVENUE TARGETS — POST (create/update) + GET (list)
# POST /admin/revenue/targets  → Admin sets monthly MRR target
# GET  /admin/revenue/targets  → Fetch targets for Revenue Trend dashed line
# =============================================================================

@revenue_dashboard_router.post(
    "/admin/revenue/targets",
    response_model=RevenueTargetResponse,
    status_code=status.HTTP_200_OK,       # 200 not 201 — upsert semantics
    summary="Create or update a monthly revenue target",
    description=(
        "Admin sets the MRR target for a specific month. "
        "target_month must be the first day of a month (e.g. 2026-01-01). "
        "Auto-normalized if a non-first day is submitted. "
        "If target for this month already exists, it is updated (upsert). "
        "The target appears as the dashed grey 'Target' line on the Revenue Trend chart."
    ),
)
async def create_revenue_target(
    payload:      RevenueTargetCreate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _admin_only,
) -> RevenueTargetResponse:
    target = await service_create_or_update_target(db, payload, current_user.user_id)
    return _build_target_response(target)


@revenue_dashboard_router.get(
    "/admin/revenue/targets",
    response_model=RevenueTargetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List revenue targets (for Revenue Trend chart)",
    description=(
        "Returns admin-set MRR targets for the given month range. "
        "Default: last 12 months + next 3 months. "
        "Frontend uses this to draw the dashed Target line on the Revenue Trend chart. "
        "Returns empty list if admin has not set any targets yet (no dashed line shown)."
    ),
)
async def list_revenue_targets(
    db:           DBSession,
    _:            Current_User = _view_billing,
    months_back:  int = Query(12, ge=1, le=24, description="How many months back to include"),
    months_ahead: int = Query(3,  ge=0, le=12, description="How many months ahead to include"),
) -> RevenueTargetListResponse:
    targets = await service_list_targets(db, months_back=months_back, months_ahead=months_ahead)
    items = [_build_target_response(t) for t in targets]
    return RevenueTargetListResponse(items=items, total=len(items))
