"""
app/services/revenue_dashboard_service.py

NEW FILE — ADMIN-08 Revenue Dashboard service layer.

WHY NEW FILE (not added to subscription_service.py):
  - subscription_service.py handles ADMIN-07 CRUD operations
  - This file handles read-only ANALYTICS queries only — no mutations
  - All queries here read from revenue_snapshots, revenue_targets,
    subscription_invoices, user_subscriptions, users, subscription_plans
  - Keeping analytics separate from CRUD is standard production practice

INTERLINK WITH EXISTING FILES:
  - Uses same DB session pattern as subscription_service.py (AsyncSession)
  - Uses same model imports from app.models.models
  - Imports subscription_models for SubscriptionInvoice etc.
  - Called exclusively by revenue_dashboard_router.py

MOUNT NOTE:
  Nothing to change in main.py for the service — only the router needs mounting.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import and_, case, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# ---------------------------------------------------------------------------
# Model imports — adjust paths to match your project structure
# ---------------------------------------------------------------------------
from app.models.visamodels import User, UserSubscription, SubscriptionInvoice
from app.models.visamodels import (
    SubscriptionPlan,
    RevenueSnapshot,
    RevenueTarget,
)

# ---------------------------------------------------------------------------
# Schema imports
# ---------------------------------------------------------------------------
from app.schemas.admin.revenue_dashboard import (
    FailingPaymentsBanner,
    FailingPaymentRow,
    FailingPaymentsDetailResponse,
    FailureCodeBreakdown,
    KPICardValue,
    PlanDistributionResponse,
    PlanDistributionSlice,
    RecentTransactionsResponse,
    RevenueDashboardKPIResponse,
    RevenueDashboardFullResponse,
    RevenueTrendPoint,
    RevenueTrendResponse,
    RevenueTargetCreate,
    RevenueTargetListResponse,
    RevenueTargetResponse,
    RevenueTargetUpdate,
    TransactionRow,
    TransactionStatusBadge,
    TrialConversionsPoint,
    TrialConversionsResponse,
)


# =============================================================================
# HELPERS
# =============================================================================

def _cents_to_display(cents: int, currency: str = "USD") -> str:
    """Convert cents to human-readable display string. e.g. 12450000 → '$124.5K'"""
    if cents == 0:
        return "$0"
    dollars = cents / 100
    if dollars >= 1_000_000:
        return f"${dollars / 1_000_000:.2f}M".rstrip("0").rstrip(".")
    if dollars >= 1_000:
        # Use K notation — trim trailing zeros
        val = dollars / 1_000
        if val == int(val):
            return f"${int(val)}K"
        return f"${val:.1f}K"
    return f"${dollars:,.2f}"


def _delta_display(current: int, previous: int) -> Tuple[str, bool]:
    """
    Compute delta percentage string and whether it's positive.
    Returns: ("+12.5%", True) or ("-0.3%", False)
    """
    if previous == 0:
        return ("N/A", True)
    delta_pct = ((current - previous) / previous) * 100
    sign = "+" if delta_pct >= 0 else ""
    return (f"{sign}{delta_pct:.1f}%", delta_pct >= 0)


def _avatar_initials(name: str) -> str:
    """
    Generate avatar initials from a name.
    "Acme Corp" → "Ac", "Sarah Jenkins" → "SJ", "Global Tech" → "GT"
    """
    parts = name.strip().split()
    if len(parts) == 1:
        return name[:2].title()
    return (parts[0][0] + parts[1][0]).upper()


def _avatar_color(initials: str) -> str:
    """
    Deterministic background color for avatar based on initials.
    Cycles through a fixed palette — same input always gives same color.
    """
    colors = [
        "#e0e7ff",  # indigo light
        "#ffedd5",  # orange light
        "#d1fae5",  # green light
        "#f3f4f6",  # gray light
        "#fce7f3",  # pink light
        "#dbeafe",  # blue light
    ]
    idx = (ord(initials[0]) + ord(initials[-1])) % len(colors)
    return colors[idx]


def _status_badge(invoice_status: str) -> TransactionStatusBadge:
    """Map invoice status to dashboard badge display."""
    mapping = {
        "paid":         TransactionStatusBadge(status="paid",     label="Success", color="green"),
        "failed":       TransactionStatusBadge(status="failed",   label="Failed",  color="red"),
        "pending":      TransactionStatusBadge(status="pending",  label="Pending", color="yellow"),
        "open":         TransactionStatusBadge(status="open",     label="Pending", color="yellow"),
        "refunded":     TransactionStatusBadge(status="refunded", label="Refunded",color="gray"),
        "void":         TransactionStatusBadge(status="void",     label="Voided",  color="gray"),
        "uncollectible":TransactionStatusBadge(status="uncollectible", label="Written Off", color="gray"),
        "draft":        TransactionStatusBadge(status="draft",    label="Draft",   color="gray"),
    }
    return mapping.get(invoice_status, TransactionStatusBadge(
        status=invoice_status, label=invoice_status.title(), color="gray"
    ))


def _failure_code_label(code: Optional[str]) -> Optional[str]:
    """Human-readable label for Stripe failure codes."""
    if not code:
        return None
    labels = {
        "card_expired":            "Expired Card",
        "insufficient_funds":      "Insufficient Funds",
        "card_declined":           "Card Declined",
        "authentication_required": "Auth Required",
        "do_not_honor":            "Bank Blocked",
        "lost_card":               "Lost Card",
        "stolen_card":             "Stolen Card",
        "other":                   "Other",
    }
    return labels.get(code, code.replace("_", " ").title())


def _get_date_range(period: str, date_from: Optional[date], date_to: Optional[date]):
    """Resolve period string to (start_date, end_date) tuple."""
    today = date.today()
    if period == "this_month":
        start = today.replace(day=1)
        end = today
    elif period == "quarter":
        # Current quarter
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=quarter_month, day=1)
        end = today
    elif period == "custom":
        start = date_from or today.replace(day=1)
        end = date_to or today
    else:  # last_12_months (default)
        start = (today - timedelta(days=365)).replace(day=1)
        end = today
    return start, end


# =============================================================================
# SERVICE 1 — KPI CARDS + FAILING PAYMENTS BANNER
# GET /admin/revenue/dashboard
# =============================================================================

async def service_get_revenue_kpis(
    db:         AsyncSession,
    period:     str = "last_12_months",
    date_from:  Optional[date] = None,
    date_to:    Optional[date] = None,
) -> RevenueDashboardKPIResponse:
    """
    Powers the 4 KPI cards + failing payments banner.

    Strategy:
      1. Try to fetch latest revenue_snapshot for current month
      2. If snapshot exists → use pre-aggregated values (fast path)
      3. If no snapshot yet → compute live from OLTP tables (slow path, testing mode)
    """
    today = date.today()
    current_month_start = today.replace(day=1)

    # ── Try snapshot fast path ────────────────────────────────────────────────
    snapshot_result = await db.execute(
        select(RevenueSnapshot)
        .where(RevenueSnapshot.snapshot_date >= current_month_start)
        .order_by(desc(RevenueSnapshot.snapshot_date))
        .limit(1)
    )
    current_snapshot = snapshot_result.scalar_one_or_none()

    # Previous month snapshot for deltas
    prev_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    prev_result = await db.execute(
        select(RevenueSnapshot)
        .where(
            RevenueSnapshot.snapshot_date >= prev_month_start,
            RevenueSnapshot.snapshot_date < current_month_start,
        )
        .order_by(desc(RevenueSnapshot.snapshot_date))
        .limit(1)
    )
    prev_snapshot = prev_result.scalar_one_or_none()

    # Last year snapshot for ARR delta
    last_year_start = current_month_start.replace(year=current_month_start.year - 1)
    last_year_result = await db.execute(
        select(RevenueSnapshot)
        .where(
            RevenueSnapshot.snapshot_date >= last_year_start,
            RevenueSnapshot.snapshot_date < last_year_start.replace(
                month=last_year_start.month % 12 + 1
            ) if last_year_start.month < 12 else
            RevenueSnapshot.snapshot_date < last_year_start.replace(year=last_year_start.year + 1, month=1, day=1),
        )
        .order_by(desc(RevenueSnapshot.snapshot_date))
        .limit(1)
    )
    last_year_snapshot = last_year_result.scalar_one_or_none()

    if current_snapshot:
        # ── FAST PATH: use snapshot ───────────────────────────────────────────
        mrr_cents  = current_snapshot.mrr_cents
        arr_cents  = current_snapshot.arr_cents
        active_sub = current_snapshot.active_subscriber_count
        new_sub    = current_snapshot.new_subscriber_count
        churn_bps  = current_snapshot.net_revenue_churn_bps

        prev_mrr   = prev_snapshot.mrr_cents if prev_snapshot else 0
        prev_arr   = prev_snapshot.arr_cents if prev_snapshot else 0
        prev_churn = prev_snapshot.net_revenue_churn_bps if prev_snapshot else 0
        ly_arr     = last_year_snapshot.arr_cents if last_year_snapshot else 0

        is_live = False
        data_as_of = current_snapshot.snapshot_date

    else:
        # ── SLOW PATH: compute live from OLTP (for testing/first-run) ─────────
        # This runs only when no snapshot exists yet
        # Not recommended for production with 1000+ subs — use snapshot job

        active_subs_result = await db.execute(
            select(
                func.count(UserSubscription.id).label("count"),
                func.sum(UserSubscription.effective_mrr_cents).label("total_mrr"),
            ).where(UserSubscription.status.in_(["active", "trialing"]))
        )
        row = active_subs_result.one()
        mrr_cents  = int(row.total_mrr or 0)
        arr_cents  = mrr_cents * 12
        active_sub = int(row.count or 0)

        # New subscribers this month
        new_sub_result = await db.execute(
            select(func.count(UserSubscription.id))
            .where(
                UserSubscription.status.in_(["active", "trialing"]),
                UserSubscription.created_at >= datetime.combine(current_month_start, datetime.min.time()),
            )
        )
        new_sub = int(new_sub_result.scalar() or 0)

        prev_mrr   = 0   # cannot compute without snapshot
        prev_arr   = 0
        prev_churn = 0
        ly_arr     = 0
        churn_bps  = 0
        is_live    = True
        data_as_of = today

    # ── Build KPICardValue objects ────────────────────────────────────────────
    mrr_delta_str, mrr_delta_pos = _delta_display(mrr_cents, prev_mrr)
    arr_delta_str, arr_delta_pos = _delta_display(arr_cents, ly_arr)
    churn_current = churn_bps / 100.0  # convert bps to pct
    churn_prev    = prev_churn / 100.0
    churn_delta   = churn_current - churn_prev
    churn_sign    = "+" if churn_delta >= 0 else ""
    churn_delta_str = f"{churn_sign}{abs(churn_delta):.1f}%"
    # For churn: higher is BAD, so delta_positive=False when churn increases
    churn_delta_pos = churn_delta <= 0

    mrr_kpi = KPICardValue(
        value_cents    = mrr_cents,
        value_display  = _cents_to_display(mrr_cents),
        delta_display  = mrr_delta_str if prev_mrr else None,
        delta_label    = "vs last month",
        delta_positive = mrr_delta_pos,
    )
    arr_kpi = KPICardValue(
        value_cents    = arr_cents,
        value_display  = _cents_to_display(arr_cents),
        delta_display  = arr_delta_str if ly_arr else None,
        delta_label    = "vs last year",
        delta_positive = arr_delta_pos,
    )
    subs_kpi = KPICardValue(
        value_display  = f"{active_sub:,}",
        delta_display  = f"+{new_sub}" if new_sub else None,
        delta_label    = "new this month",
        delta_positive = True,
    )
    churn_kpi = KPICardValue(
        value_display  = f"{churn_current:.1f}%",
        delta_display  = churn_delta_str if prev_churn else None,
        delta_label    = "vs last month",
        delta_positive = churn_delta_pos,
    )

    # ── Failing payments banner ───────────────────────────────────────────────
    failing_banner = await _get_failing_payments_banner(db)

    return RevenueDashboardKPIResponse(
        mrr                 = mrr_kpi,
        arr                 = arr_kpi,
        active_subscribers  = subs_kpi,
        net_revenue_churn   = churn_kpi,
        failing_payments    = failing_banner,
        data_as_of          = data_as_of,
        is_live             = is_live,
    )


async def _get_failing_payments_banner(db: AsyncSession) -> Optional[FailingPaymentsBanner]:
    """
    Compute the failing payments alert banner data.
    Queries live from subscription_invoices (not snapshots — needs to be real-time).
    """
    # Count failing invoices + sum MRR at risk
    failing_result = await db.execute(
        select(
            func.count(SubscriptionInvoice.id).label("count"),
            func.sum(UserSubscription.effective_mrr_cents).label("mrr_at_risk"),
        )
        .join(UserSubscription, SubscriptionInvoice.subscription_id == UserSubscription.id)
        .where(SubscriptionInvoice.status == "failed")
    )
    row = failing_result.one()
    count = int(row.count or 0)
    if count == 0:
        return None

    mrr_at_risk = int(row.mrr_at_risk or 0)

    # Breakdown by failure_code
    breakdown_result = await db.execute(
        select(
            SubscriptionInvoice.failure_code,
            func.count(SubscriptionInvoice.id).label("cnt"),
            func.sum(UserSubscription.effective_mrr_cents).label("mrr"),
        )
        .join(UserSubscription, SubscriptionInvoice.subscription_id == UserSubscription.id)
        .where(SubscriptionInvoice.status == "failed")
        .group_by(SubscriptionInvoice.failure_code)
    )
    breakdown_rows = breakdown_result.all()

    breakdown = [
        FailureCodeBreakdown(
            failure_code         = r.failure_code or "other",
            label                = _failure_code_label(r.failure_code) or "Other",
            count                = int(r.cnt),
            mrr_at_risk_cents    = int(r.mrr or 0),
            mrr_at_risk_display  = _cents_to_display(int(r.mrr or 0)),
        )
        for r in breakdown_rows
    ]

    return FailingPaymentsBanner(
        count                = count,
        mrr_at_risk_cents    = mrr_at_risk,
        mrr_at_risk_display  = _cents_to_display(mrr_at_risk),
        by_failure_code      = breakdown,
    )


# =============================================================================
# SERVICE 2 — REVENUE TREND CHART
# GET /admin/revenue/trend
# =============================================================================

async def service_get_revenue_trend(
    db:            AsyncSession,
    period_months: int = 12,
    period:        str = "last_12_months",
    date_from:     Optional[date] = None,
    date_to:       Optional[date] = None,
) -> RevenueTrendResponse:
    """
    Returns monthly MRR data points for the Revenue Trend line chart.
    Also fetches Revenue Targets to overlay as the dashed line.
    """
    today = date.today()
    start_date = (today - timedelta(days=period_months * 31)).replace(day=1)

    # ── Fetch snapshots ───────────────────────────────────────────────────────
    snapshots_result = await db.execute(
        select(RevenueSnapshot)
        .where(RevenueSnapshot.snapshot_date >= start_date)
        .order_by(RevenueSnapshot.snapshot_date.asc())
    )
    snapshots = snapshots_result.scalars().all()

    # ── Fetch targets ─────────────────────────────────────────────────────────
    targets_result = await db.execute(
        select(RevenueTarget)
        .where(RevenueTarget.target_month >= start_date)
        .order_by(RevenueTarget.target_month.asc())
    )
    targets = targets_result.scalars().all()
    targets_by_month = {
        t.target_month.strftime("%Y-%m"): t.target_mrr_cents
        for t in targets
    }

    # ── If no snapshots, compute live (testing mode) ──────────────────────────
    if not snapshots:
        return await _compute_trend_live(db, period_months, targets_by_month)

    # ── Build data points from snapshots ──────────────────────────────────────
    # Group snapshots by month — take the LAST snapshot of each month
    month_snapshots: dict[str, RevenueSnapshot] = {}
    for s in snapshots:
        month_key = s.snapshot_date.strftime("%Y-%m")
        month_snapshots[month_key] = s   # last one wins (most recent in month)

    data_points = []
    max_mrr = 0
    for month_key, snap in sorted(month_snapshots.items()):
        snap_date = datetime.strptime(month_key, "%Y-%m").date()
        target = targets_by_month.get(month_key)
        mrr = snap.mrr_cents
        max_mrr = max(max_mrr, mrr, target or 0)

        data_points.append(RevenueTrendPoint(
            month_label         = snap_date.strftime("%b"),   # "Jan"
            month_date          = month_key,                   # "2026-01"
            mrr_cents           = mrr,
            mrr_display         = _cents_to_display(mrr),
            target_mrr_cents    = target,
            target_mrr_display  = _cents_to_display(target) if target else None,
        ))

    # ── Y-axis bounds (round up to nearest $20K step) ─────────────────────────
    max_dollars = math.ceil((max_mrr / 100) / 20000) * 20000
    y_max_cents  = max_dollars * 100
    y_step_cents = (max_dollars // 6) * 100   # 6 grid lines

    return RevenueTrendResponse(
        data_points        = data_points,
        period_months      = period_months,
        y_axis_max_cents   = y_max_cents,
        y_axis_step_cents  = y_step_cents,
    )


async def _compute_trend_live(
    db: AsyncSession,
    period_months: int,
    targets_by_month: dict,
) -> RevenueTrendResponse:
    """
    TESTING FALLBACK: Compute MRR trend live from OLTP data.
    Works only for current active subscriptions — cannot show historical accurately.
    In production use revenue_snapshots.
    """
    today = date.today()
    current_mrr_result = await db.execute(
        select(func.sum(UserSubscription.effective_mrr_cents))
        .where(UserSubscription.status.in_(["active", "trialing"]))
    )
    current_mrr = int(current_mrr_result.scalar() or 0)

    # Generate N months of data points — all showing current MRR
    # (since we have no historical data without snapshots)
    data_points = []
    max_mrr = current_mrr
    for i in range(period_months - 1, -1, -1):
        snap_date = (today - timedelta(days=i * 30)).replace(day=1)
        month_key = snap_date.strftime("%Y-%m")
        target = targets_by_month.get(month_key)
        max_mrr = max(max_mrr, target or 0)

        data_points.append(RevenueTrendPoint(
            month_label         = snap_date.strftime("%b"),
            month_date          = month_key,
            mrr_cents           = current_mrr,    # flat line — no historical data
            mrr_display         = _cents_to_display(current_mrr),
            target_mrr_cents    = target,
            target_mrr_display  = _cents_to_display(target) if target else None,
        ))

    max_dollars = math.ceil((max_mrr / 100) / 20000) * 20000 or 20000
    return RevenueTrendResponse(
        data_points        = data_points,
        period_months      = period_months,
        y_axis_max_cents   = max_dollars * 100,
        y_axis_step_cents  = (max_dollars // 6) * 100,
    )


# =============================================================================
# SERVICE 3 — PLAN DISTRIBUTION DONUT
# GET /admin/revenue/plan-distribution
# =============================================================================

async def service_get_plan_distribution(
    db: AsyncSession,
) -> PlanDistributionResponse:
    """
    Returns MRR breakdown by plan for the donut chart.
    Fast path: reads mrr_by_plan JSON from latest snapshot.
    Slow path: computes live from user_subscriptions.
    """
    # Try snapshot
    today = date.today()
    current_month_start = today.replace(day=1)
    snap_result = await db.execute(
        select(RevenueSnapshot)
        .where(RevenueSnapshot.snapshot_date >= current_month_start)
        .order_by(desc(RevenueSnapshot.snapshot_date))
        .limit(1)
    )
    snap = snap_result.scalar_one_or_none()

    # Plan colors matching the Figma design
    plan_colors = {
        "enterprise":    "#764ba2",   # purple
        "professional":  "#667eea",   # indigo
        "starter":       "#a3bffa",   # light blue
        "free":          "#d1d5db",   # gray
    }

    if snap and snap.mrr_by_plan:
        mrr_by_plan = json.loads(snap.mrr_by_plan)
        total_mrr = sum(mrr_by_plan.values())
        if total_mrr == 0:
            total_mrr = 1  # avoid division by zero

        slices = []
        # Fetch plan names for display
        plan_result = await db.execute(select(SubscriptionPlan))
        plans = {p.slug: p.name for p in plan_result.scalars().all()}

        for slug, mrr_cents in sorted(mrr_by_plan.items(), key=lambda x: -x[1]):
            if mrr_cents == 0:
                continue
            slices.append(PlanDistributionSlice(
                plan_name   = plans.get(slug, slug.title()),
                plan_slug   = slug,
                mrr_cents   = mrr_cents,
                mrr_display = _cents_to_display(mrr_cents),
                percentage  = round(mrr_cents / total_mrr * 100, 1),
                color       = plan_colors.get(slug, "#94a3b8"),
            ))
    else:
        # Live computation from user_subscriptions
        live_result = await db.execute(
            select(
                SubscriptionPlan.slug,
                SubscriptionPlan.name,
                func.sum(UserSubscription.effective_mrr_cents).label("mrr"),
            )
            .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
            .where(UserSubscription.status.in_(["active", "trialing"]))
            .group_by(SubscriptionPlan.slug, SubscriptionPlan.name)
            .order_by(desc("mrr"))
        )
        rows = live_result.all()
        total_mrr = sum(int(r.mrr or 0) for r in rows) or 1

        slices = [
            PlanDistributionSlice(
                plan_name   = r.name,
                plan_slug   = r.slug,
                mrr_cents   = int(r.mrr or 0),
                mrr_display = _cents_to_display(int(r.mrr or 0)),
                percentage  = round(int(r.mrr or 0) / total_mrr * 100, 1),
                color       = plan_colors.get(r.slug, "#94a3b8"),
            )
            for r in rows if int(r.mrr or 0) > 0
        ]

    total_actual = sum(s.mrr_cents for s in slices)
    return PlanDistributionResponse(
        slices             = slices,
        total_mrr_cents    = total_actual,
        total_mrr_display  = _cents_to_display(total_actual),
    )


# =============================================================================
# SERVICE 4 — RECENT TRANSACTIONS TABLE
# GET /admin/revenue/transactions
# =============================================================================

async def service_get_recent_transactions(
    db:            AsyncSession,
    page:          int = 1,
    page_size:     int = 10,
    status_filter: Optional[str] = None,
    date_from:     Optional[date] = None,
    date_to:       Optional[date] = None,
) -> RecentTransactionsResponse:
    """
    Powers the Recent Transactions table at bottom-left of ADMIN-08.
    Joins invoices → subscriptions → users → plans.
    """
    # Build query
    query = (
        select(
            SubscriptionInvoice,
            User.id.label("user_id"),
            (User.first_name + " " + User.last_name).label("user_name"),
            User.email.label("user_email"),
            SubscriptionPlan.name.label("plan_name"),
            SubscriptionPlan.slug.label("plan_slug"),
            UserSubscription.effective_mrr_cents.label("sub_mrr"),
        )
        .join(UserSubscription, SubscriptionInvoice.subscription_id == UserSubscription.id)
        .join(User, UserSubscription.user_id == User.id)
        .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
        .order_by(desc(SubscriptionInvoice.created_at))
    )

    if status_filter:
        query = query.where(SubscriptionInvoice.status == status_filter)
    if date_from:
        query = query.where(SubscriptionInvoice.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(SubscriptionInvoice.created_at <= datetime.combine(date_to, datetime.max.time()))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = int(total_result.scalar() or 0)

    # Paginate
    offset = (page - 1) * page_size
    paginated = query.limit(page_size).offset(offset)
    result = await db.execute(paginated)
    rows = result.all()

    items = []
    for row in rows:
        inv = row[0]
        user_name = row.user_name or "Unknown"
        initials  = _avatar_initials(user_name)
        tx_date   = inv.created_at

        items.append(TransactionRow(
            invoice_id        = inv.id,
            invoice_number    = inv.invoice_number,
            user_id           = row.user_id,
            user_name         = user_name,
            user_email        = row.user_email,
            avatar_initials   = initials,
            avatar_color      = _avatar_color(initials),
            amount_cents      = inv.total_cents,
            amount_display    = f"${inv.total_cents / 100:,.2f}",
            plan_name         = row.plan_name or "",
            plan_slug         = row.plan_slug or "",
            transaction_date  = tx_date,
            date_display      = tx_date.strftime("%b %d, %Y") if tx_date else "",
            status            = _status_badge(inv.status),
            failure_code      = getattr(inv, "failure_code", None),
            stripe_invoice_id = inv.stripe_invoice_id,
        ))

    return RecentTransactionsResponse(
        items       = items,
        total       = total,
        page        = page,
        page_size   = page_size,
        total_pages = max(1, math.ceil(total / page_size)),
    )


# =============================================================================
# SERVICE 5 — TRIAL CONVERSIONS BAR CHART
# GET /admin/revenue/trial-conversions
# =============================================================================

async def service_get_trial_conversions(
    db:            AsyncSession,
    period_months: int = 6,
) -> TrialConversionsResponse:
    """
    Powers the Trial Conversions bar chart.
    Shows conversion vs churn over N months.
    """
    today = date.today()
    start_date = (today - timedelta(days=period_months * 31)).replace(day=1)

    # Try snapshots first
    snap_result = await db.execute(
        select(RevenueSnapshot)
        .where(RevenueSnapshot.snapshot_date >= start_date)
        .order_by(RevenueSnapshot.snapshot_date.asc())
    )
    snapshots = snap_result.scalars().all()

    # Group by month
    month_snaps: dict[str, RevenueSnapshot] = {}
    for s in snapshots:
        mk = s.snapshot_date.strftime("%Y-%m")
        month_snaps[mk] = s

    data_points = []
    total_new = total_converted = total_churned = 0

    if month_snaps:
        for month_key, snap in sorted(month_snaps.items()):
            snap_date = datetime.strptime(month_key, "%Y-%m").date()
            new    = snap.new_trial_count
            conv   = snap.converted_trial_count
            churn  = snap.churned_trial_count
            rate   = round(conv / new * 100, 1) if new > 0 else 0.0

            total_new       += new
            total_converted += conv
            total_churned   += churn

            data_points.append(TrialConversionsPoint(
                month_label          = snap_date.strftime("%b"),
                month_date           = month_key,
                new_trials           = new,
                converted_trials     = conv,
                churned_trials       = churn,
                conversion_rate_pct  = rate,
            ))
    else:
        # Live fallback: approximate from user_subscriptions
        for i in range(period_months - 1, -1, -1):
            snap_date = (today - timedelta(days=i * 30)).replace(day=1)
            month_end = (snap_date.replace(month=snap_date.month % 12 + 1, day=1)
                         if snap_date.month < 12
                         else snap_date.replace(year=snap_date.year + 1, month=1, day=1))

            new_result = await db.execute(
                select(func.count(UserSubscription.id))
                .where(
                    UserSubscription.trial_start >= datetime.combine(snap_date, datetime.min.time()),
                    UserSubscription.trial_start < datetime.combine(month_end, datetime.min.time()),
                )
            )
            new = int(new_result.scalar() or 0)

            conv_result = await db.execute(
                select(func.count(UserSubscription.id))
                .where(
                    UserSubscription.trial_end >= datetime.combine(snap_date, datetime.min.time()),
                    UserSubscription.trial_end < datetime.combine(month_end, datetime.min.time()),
                    UserSubscription.status == "active",
                )
            )
            conv = int(conv_result.scalar() or 0)
            churn = max(0, new - conv)
            rate  = round(conv / new * 100, 1) if new > 0 else 0.0

            total_new       += new
            total_converted += conv
            total_churned   += churn

            data_points.append(TrialConversionsPoint(
                month_label         = snap_date.strftime("%b"),
                month_date          = snap_date.strftime("%Y-%m"),
                new_trials          = new,
                converted_trials    = conv,
                churned_trials      = churn,
                conversion_rate_pct = rate,
            ))

    avg_rate = round(total_converted / total_new * 100, 1) if total_new > 0 else 0.0

    return TrialConversionsResponse(
        data_points             = data_points,
        period_months           = period_months,
        total_new_trials        = total_new,
        total_converted         = total_converted,
        total_churned           = total_churned,
        avg_conversion_rate_pct = avg_rate,
    )


# =============================================================================
# SERVICE 6 — FAILING PAYMENTS DETAIL LIST
# GET /admin/revenue/failing-payments
# =============================================================================

async def service_get_failing_payments(
    db:        AsyncSession,
    page:      int = 1,
    page_size: int = 20,
) -> FailingPaymentsDetailResponse:
    """
    Full list of failing payments for the Review modal.
    Triggered by "Review Failing Payments" button.
    """
    query = (
        select(
            SubscriptionInvoice,
            User.id.label("user_id"),
            (User.first_name + " " + User.last_name).label("user_name"),
            User.email.label("user_email"),
            SubscriptionPlan.name.label("plan_name"),
            UserSubscription.effective_mrr_cents.label("mrr"),
        )
        .join(UserSubscription, SubscriptionInvoice.subscription_id == UserSubscription.id)
        .join(User, UserSubscription.user_id == User.id)
        .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
        .where(SubscriptionInvoice.status == "failed")
        .order_by(desc(SubscriptionInvoice.updated_at))
    )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = int(count_result.scalar() or 0)

    mrr_result = await db.execute(
        select(func.sum(UserSubscription.effective_mrr_cents))
        .join(SubscriptionInvoice, SubscriptionInvoice.subscription_id == UserSubscription.id)
        .where(SubscriptionInvoice.status == "failed")
    )
    total_mrr_at_risk = int(mrr_result.scalar() or 0)

    offset = (page - 1) * page_size
    rows_result = await db.execute(query.limit(page_size).offset(offset))
    rows = rows_result.all()

    items = []
    for row in rows:
        inv  = row[0]
        name = row.user_name or "Unknown"
        initials = _avatar_initials(name)

        items.append(FailingPaymentRow(
            invoice_id          = inv.id,
            invoice_number      = inv.invoice_number,
            user_id             = row.user_id,
            user_name           = name,
            user_email          = row.user_email,
            avatar_initials     = initials,
            amount_cents        = inv.total_cents,
            amount_display      = f"${inv.total_cents / 100:,.2f}",
            plan_name           = row.plan_name or "",
            attempt_count       = inv.attempt_count,
            next_attempt_at     = inv.next_attempt_at,
            failed_at           = inv.updated_at,
            failure_code        = getattr(inv, "failure_code", None),
            failure_label       = _failure_code_label(getattr(inv, "failure_code", None)),
            mrr_at_risk_cents   = int(row.mrr or 0),
            mrr_at_risk_display = _cents_to_display(int(row.mrr or 0)),
            stripe_invoice_id   = inv.stripe_invoice_id,
        ))

    return FailingPaymentsDetailResponse(
        items                      = items,
        total                      = total,
        total_mrr_at_risk_cents    = total_mrr_at_risk,
        total_mrr_at_risk_display  = _cents_to_display(total_mrr_at_risk),
        page                       = page,
        page_size                  = page_size,
        total_pages                = max(1, math.ceil(total / page_size)),
    )


# =============================================================================
# SERVICE 7 — REVENUE TARGETS CRUD
# POST + GET + PATCH /admin/revenue/targets
# =============================================================================

async def service_create_or_update_target(
    db:         AsyncSession,
    payload:    RevenueTargetCreate,
    created_by: uuid.UUID,
) -> RevenueTarget:
    """
    Create or update a revenue target for a month.
    Uses upsert logic — if target_month already exists, update it.
    """
    # Check if exists
    existing = await db.execute(
        select(RevenueTarget).where(RevenueTarget.target_month == payload.target_month)
    )
    target = existing.scalar_one_or_none()

    if target:
        target.target_mrr_cents = payload.target_mrr_cents
        target.notes            = payload.notes
        target.modified_by      = created_by
        target.updated_at       = datetime.now(timezone.utc)
    else:
        target = RevenueTarget(
            target_month      = payload.target_month,
            target_mrr_cents  = payload.target_mrr_cents,
            notes             = payload.notes,
            created_by        = created_by,
            modified_by       = created_by,
        )
        db.add(target)

    await db.commit()
    await db.refresh(target)
    return target


async def service_list_targets(
    db:           AsyncSession,
    months_back:  int = 12,
    months_ahead: int = 3,
) -> List[RevenueTarget]:
    """
    Returns revenue targets for the given range.
    Used by the Revenue Trend chart (dashed target line).
    """
    today = date.today()
    start = (today - timedelta(days=months_back * 31)).replace(day=1)
    end   = (today + timedelta(days=months_ahead * 31)).replace(day=1)

    result = await db.execute(
        select(RevenueTarget)
        .where(
            RevenueTarget.target_month >= start,
            RevenueTarget.target_month <= end,
        )
        .order_by(RevenueTarget.target_month.asc())
    )
    return result.scalars().all()


def _build_target_response(target: RevenueTarget) -> RevenueTargetResponse:
    """Add computed display fields to a RevenueTarget ORM object."""
    r = RevenueTargetResponse.model_validate(target)
    object.__setattr__(r, "target_month_label",
                       target.target_month.strftime("%B %Y"))        # "January 2026"
    object.__setattr__(r, "target_mrr_display",
                       _cents_to_display(target.target_mrr_cents))   # "$120K"
    return r


# =============================================================================
# SERVICE 8 — FULL DASHBOARD (single call)
# GET /admin/revenue/dashboard/full
# =============================================================================

async def service_get_full_dashboard(
    db:     AsyncSession,
    period: str = "last_12_months",
) -> RevenueDashboardFullResponse:
    """
    Aggregates all dashboard sections into one response.
    Useful for dashboard initial load — avoids 5 waterfall requests.
    """
    kpi   = await service_get_revenue_kpis(db, period=period)
    trend = await service_get_revenue_trend(db, period=period)
    dist  = await service_get_plan_distribution(db)
    txns  = await service_get_recent_transactions(db, page=1, page_size=5)
    conv  = await service_get_trial_conversions(db, period_months=6)

    return RevenueDashboardFullResponse(
        kpi               = kpi,
        trend             = trend,
        plan_distribution = dist,
        transactions      = txns,
        trial_conversions = conv,
        generated_at      = datetime.now(timezone.utc),
    )


# =============================================================================
# SERVICE 9 — EXPORT REPORT (CSV)
# GET /admin/revenue/export
# =============================================================================

async def service_export_revenue_report(
    db:                     AsyncSession,
    period:                 str = "last_12_months",
    date_from:              Optional[date] = None,
    date_to:                Optional[date] = None,
    include_transactions:   bool = True,
    include_kpi_summary:    bool = True,
    include_plan_breakdown: bool = True,
) -> str:
    """
    Generates a CSV string for the Export Report button.
    Returns raw CSV string — router wraps it in StreamingResponse.
    """
    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)

    start_date, end_date = _get_date_range(period, date_from, date_to)

    if include_kpi_summary:
        writer.writerow(["=== REVENUE DASHBOARD SUMMARY ==="])
        writer.writerow(["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
        writer.writerow(["Period", f"{start_date} to {end_date}"])
        writer.writerow([])

        kpi = await service_get_revenue_kpis(db, period=period, date_from=date_from, date_to=date_to)
        writer.writerow(["Metric", "Value", "Delta"])
        writer.writerow(["Monthly Recurring Revenue", kpi.mrr.value_display, kpi.mrr.delta_display or ""])
        writer.writerow(["Annual Run Rate",            kpi.arr.value_display, kpi.arr.delta_display or ""])
        writer.writerow(["Active Subscribers",         kpi.active_subscribers.value_display, kpi.active_subscribers.delta_display or ""])
        writer.writerow(["Net Revenue Churn",          kpi.net_revenue_churn.value_display,  kpi.net_revenue_churn.delta_display or ""])
        if kpi.failing_payments:
            writer.writerow(["Failing Payments",       str(kpi.failing_payments.count), kpi.failing_payments.mrr_at_risk_display + " at risk"])
        writer.writerow([])

    if include_plan_breakdown:
        writer.writerow(["=== PLAN DISTRIBUTION ==="])
        writer.writerow(["Plan", "MRR", "Percentage"])
        dist = await service_get_plan_distribution(db)
        for s in dist.slices:
            writer.writerow([s.plan_name, s.mrr_display, f"{s.percentage}%"])
        writer.writerow([])

    if include_transactions:
        writer.writerow(["=== RECENT TRANSACTIONS ==="])
        writer.writerow(["Customer", "Email", "Amount", "Plan", "Date", "Status"])

        txns = await service_get_recent_transactions(
            db, page=1, page_size=500,
            date_from=start_date, date_to=end_date,
        )
        for t in txns.items:
            writer.writerow([
                t.user_name,
                t.user_email,
                t.amount_display,
                t.plan_name,
                t.date_display,
                t.status.label,
            ])

    return output.getvalue()
