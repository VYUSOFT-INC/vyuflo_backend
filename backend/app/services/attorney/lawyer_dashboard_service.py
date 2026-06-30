"""
lawyer_dashboard_service.py — Service layer for 25 - Lawyer Dashboard.

"""

from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import (
    Application,
    ApplicationTask,
    AttorneyInvoice,
    AttorneyProfile,
    Deadline,
    Role,
    TimeEntry,
    User,
    UserProfile,
    UserRole,
    VisaType,
)
from app.schemas.attorney.lawyer_dashboard import (
    DashboardKpiCards,
    LawyerDashboardResponse,
    MonthlyBillingResponse,
    RecentCaseItem,
    RecentCasesResponse,
)


# ===========================================================================
# CONSTANTS
# ===========================================================================

_ACTIVE_STATUSES = ("in_progress", "action_needed", "rfe_response")

_STATUS_LABELS = {
    "draft":         "Draft",
    "in_progress":   "In Progress",
    "action_needed": "Action Required",
    "rfe_response":  "RFE Response",
    "submitted":     "Submitted",
    "approved":      "Approved",
    "rejected":      "Rejected",
    "withdrawn":     "Withdrawn",
}


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

def _month_bounds(year: int, month: int):
    """Returns (start, end) datetime for a given year/month in UTC."""
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


# ===========================================================================
# A. KPI CARDS
# ===========================================================================

async def _get_kpi_cards(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    now:         datetime,
) -> DashboardKpiCards:
    today     = now.date()
    week_ago  = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # ── Card 1: Active Cases ──────────────────────────────────────────────────
    active_q = await db.execute(
        select(func.count(Application.id)).where(
            Application.assigned_attorney_id == attorney_id,
            Application.status.in_(_ACTIVE_STATUSES),
        )
    )
    active_cases = active_q.scalar() or 0

    # Delta: cases created in last 7 days
    delta_q = await db.execute(
        select(func.count(Application.id)).where(
            Application.assigned_attorney_id == attorney_id,
            Application.status.in_(_ACTIVE_STATUSES),
            Application.created_at           >= week_ago,
        )
    )
    active_cases_delta = delta_q.scalar() or 0

    # ── Card 2: Unbilled Hours ────────────────────────────────────────────────
    unbilled_q = await db.execute(
        select(
            func.coalesce(func.sum(TimeEntry.duration_minutes), 0).label("minutes"),
            func.coalesce(func.sum(TimeEntry.amount_cents),     0).label("amount"),
        ).where(
            TimeEntry.attorney_id == attorney_id,
            TimeEntry.status      == "unbilled",
        )
    )
    unbilled_row   = unbilled_q.one()
    unbilled_hours = round(unbilled_row.minutes / 60, 1)
    unbilled_cents = unbilled_row.amount

    # ── Card 3: Deadlines Today ───────────────────────────────────────────────
    deadlines_q = await db.execute(
        select(func.count(Deadline.id)).where(
            Deadline.user_id       == attorney_id,
            func.date(Deadline.due_date) == today,
            Deadline.is_completed  == False,   # noqa: E712
            Deadline.is_dismissed  == False,   # noqa: E712
        )
    )
    deadlines_today = deadlines_q.scalar() or 0

    # ── Card 4: New Client Intakes ────────────────────────────────────────────
    intakes_q = await db.execute(
        select(func.count(Application.id)).where(
            Application.assigned_attorney_id == attorney_id,
            Application.status               == "draft",
            Application.created_at           >= month_ago,
        )
    )
    new_client_intakes = intakes_q.scalar() or 0

    return DashboardKpiCards(
        active_cases            = active_cases,
        active_cases_delta_week = active_cases_delta,
        unbilled_hours          = unbilled_hours,
        unbilled_amount_cents   = unbilled_cents,
        deadlines_today         = deadlines_today,
        requires_action         = deadlines_today > 0,
        new_client_intakes      = new_client_intakes,
        pending_review          = new_client_intakes,
    )


# ===========================================================================
# B. RECENT CASES
# ===========================================================================

async def _get_recent_cases(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    limit:       int = 5,
) -> RecentCasesResponse:
    """
    Last N applications assigned to this attorney, newest first.
    Enriched with client name, visa_type_code, status_label, next_action.
    """
    apps_q = await db.execute(
        select(Application)
        .where(Application.assigned_attorney_id == attorney_id)
        .order_by(Application.updated_at.desc())
        .limit(limit)
    )
    applications = apps_q.scalars().all()

    # Total count for "View All" link
    total_q = await db.execute(
        select(func.count(Application.id)).where(
            Application.assigned_attorney_id == attorney_id
        )
    )
    total = total_q.scalar() or 0

    items = []
    for app in applications:
        # Client name from User
        user_q = await db.execute(
            select(User.first_name, User.last_name, UserProfile.profile_picture_url)
            .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
            .where(User.id == app.user_id)
        )
        user_row = user_q.one_or_none()
        client_name      = f"{user_row.first_name} {user_row.last_name}".strip() if user_row else "Unknown"
        client_avatar_url = user_row.profile_picture_url if user_row else None

        # Visa type code
        vt_q = await db.execute(
            select(VisaType.code).where(VisaType.id == app.visa_type_id)
        )
        visa_code = vt_q.scalar_one_or_none() or "—"

        # Next action — first incomplete task
        task_q = await db.execute(
            select(ApplicationTask.task_name)
            .where(
                ApplicationTask.application_id == app.id,
                ApplicationTask.is_completed   == False,  # noqa: E712
            )
            .order_by(ApplicationTask.sort_order.asc())
            .limit(1)
        )
        next_action = task_q.scalar_one_or_none()

        # Fallback to action_required_note if no task
        if not next_action and app.action_required_note:
            next_action = app.action_required_note

        items.append(RecentCaseItem(
            application_id     = app.id,
            application_number = app.application_number,
            client_name        = client_name,
            client_avatar_url  = client_avatar_url,
            visa_type_code     = visa_code,
            status             = app.status,
            status_label       = _STATUS_LABELS.get(app.status, app.status),
            next_action        = next_action,
            updated_at         = app.updated_at,
        ))

    return RecentCasesResponse(items=items, total=total)


# ===========================================================================
# C. MONTHLY BILLING PANEL
# ===========================================================================

async def _get_monthly_billing(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    now:         datetime,
) -> MonthlyBillingResponse:
    """
    Computes the Monthly Billing panel data.
    this_month_billed, last_month_billed, MoM %, target, progress bar,
    billed hours, unbilled hours.
    """
    this_start, this_end = _month_bounds(now.year, now.month)
    last_month = now.month - 1 if now.month > 1 else 12
    last_year  = now.year if now.month > 1 else now.year - 1
    last_start, last_end = _month_bounds(last_year, last_month)

    # ── This month invoiced total ─────────────────────────────────────────────
    this_q = await db.execute(
        select(func.coalesce(func.sum(AttorneyInvoice.total_cents), 0)).where(
            AttorneyInvoice.attorney_id == attorney_id,
            AttorneyInvoice.status.in_(["sent", "paid"]),
            AttorneyInvoice.issued_date >= this_start.date(),
            AttorneyInvoice.issued_date <  this_end.date(),
        )
    )
    this_month_cents = this_q.scalar() or 0

    # ── Last month invoiced total ─────────────────────────────────────────────
    last_q = await db.execute(
        select(func.coalesce(func.sum(AttorneyInvoice.total_cents), 0)).where(
            AttorneyInvoice.attorney_id == attorney_id,
            AttorneyInvoice.status.in_(["sent", "paid"]),
            AttorneyInvoice.issued_date >= last_start.date(),
            AttorneyInvoice.issued_date <  last_end.date(),
        )
    )
    last_month_cents = last_q.scalar() or 0

    # MoM change %
    if last_month_cents > 0:
        mom_pct = round((this_month_cents - last_month_cents) / last_month_cents * 100, 1)
    else:
        mom_pct = 0.0
    mom_positive = mom_pct >= 0

    # ── Billing target from attorney_profiles ─────────────────────────────────
    ap_q = await db.execute(
        select(AttorneyProfile.monthly_billing_target_cents).where(
            AttorneyProfile.user_id == attorney_id
        )
    )
    target_cents = ap_q.scalar_one_or_none()
    target_pct   = None
    if target_cents and target_cents > 0:
        target_pct = round(this_month_cents / target_cents * 100, 1)

    # ── Billed hours this month ───────────────────────────────────────────────
    billed_q = await db.execute(
        select(func.coalesce(func.sum(TimeEntry.duration_minutes), 0)).where(
            TimeEntry.attorney_id == attorney_id,
            TimeEntry.status.in_(["invoiced", "paid"]),
            TimeEntry.entry_date  >= this_start.date(),
            TimeEntry.entry_date  <  this_end.date(),
        )
    )
    billed_minutes = billed_q.scalar() or 0
    billed_hours   = round(billed_minutes / 60, 1)

    # ── Unbilled hours (all time, not just this month) ────────────────────────
    unbilled_q = await db.execute(
        select(func.coalesce(func.sum(TimeEntry.duration_minutes), 0)).where(
            TimeEntry.attorney_id == attorney_id,
            TimeEntry.status      == "unbilled",
        )
    )
    unbilled_minutes = unbilled_q.scalar() or 0
    unbilled_hours   = round(unbilled_minutes / 60, 1)

    return MonthlyBillingResponse(
        monthly_billed_cents = this_month_cents,
        mom_change_pct       = abs(mom_pct),
        mom_positive         = mom_positive,
        target_cents         = target_cents,
        target_pct           = target_pct,
        billed_hours         = billed_hours,
        unbilled_hours       = unbilled_hours,
    )


# ===========================================================================
# D. FULL DASHBOARD
# ===========================================================================

async def get_dashboard(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
) -> LawyerDashboardResponse:
    """
    Full Screen 25 payload — KPI cards + recent cases + monthly billing.

    Today's Schedule and Critical Deadlines are NOT fetched here.
    Frontend calls existing endpoints separately:
      GET /calendar/agenda    → Today's Schedule
      GET /calendar/deadlines → Critical Deadlines
    """
    now = datetime.now(timezone.utc)

    # Attorney name + role for greeting
    user_q = await db.execute(
        select(User.first_name)
        .where(User.id == attorney_id)
    )
    first_name = user_q.scalar_one_or_none() or "Attorney"

    role_q = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == attorney_id)
        .limit(1)
    )
    role_name = role_q.scalar_one_or_none()

    kpi_cards, recent_cases, monthly_billing = await _get_kpi_cards(db, attorney_id, now), \
                                               await _get_recent_cases(db, attorney_id), \
                                               await _get_monthly_billing(db, attorney_id, now)

    return LawyerDashboardResponse(
        attorney_first_name = first_name,
        attorney_role       = role_name,
        greeting_date       = now.date(),
        kpi_cards           = kpi_cards,
        recent_cases        = recent_cases,
        monthly_billing     = monthly_billing,
    )


# ===========================================================================
# E. RECENT CASES — standalone (for "View All" link)
# ===========================================================================

async def get_recent_cases(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    limit:       int = 20,
    offset:      int = 0,
) -> RecentCasesResponse:
    """
    Paginated recent cases for the "View All" link on Screen 25.
    Same shape as the dashboard table but supports pagination.
    """
    apps_q = await db.execute(
        select(Application)
        .where(Application.assigned_attorney_id == attorney_id)
        .order_by(Application.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    applications = apps_q.scalars().all()

    total_q = await db.execute(
        select(func.count(Application.id)).where(
            Application.assigned_attorney_id == attorney_id
        )
    )
    total = total_q.scalar() or 0

    items = []
    for app in applications:
        user_q = await db.execute(
            select(User.first_name, User.last_name, UserProfile.profile_picture_url)
            .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
            .where(User.id == app.user_id)
        )
        user_row = user_q.one_or_none()
        client_name       = f"{user_row.first_name} {user_row.last_name}".strip() if user_row else "Unknown"
        client_avatar_url = user_row.profile_picture_url if user_row else None

        vt_q = await db.execute(
            select(VisaType.code).where(VisaType.id == app.visa_type_id)
        )
        visa_code = vt_q.scalar_one_or_none() or "—"

        task_q = await db.execute(
            select(ApplicationTask.task_name)
            .where(
                ApplicationTask.application_id == app.id,
                ApplicationTask.is_completed   == False,  # noqa: E712
            )
            .order_by(ApplicationTask.sort_order.asc())
            .limit(1)
        )
        next_action = task_q.scalar_one_or_none() or app.action_required_note

        items.append(RecentCaseItem(
            application_id     = app.id,
            application_number = app.application_number,
            client_name        = client_name,
            client_avatar_url  = client_avatar_url,
            visa_type_code     = visa_code,
            status             = app.status,
            status_label       = _STATUS_LABELS.get(app.status, app.status),
            next_action        = next_action,
            updated_at         = app.updated_at,
        ))

    return RecentCasesResponse(items=items, total=total)
