"""
analytics_service.py — Service layer for Lawyer Analytics Dashboard (Screen 23).

FILE LOCATION
    app/services/attorney/analytics_service.py

All data is derived from existing tables — NO new tables required:
  Application, ApplicationTask, User, UserProfile, VisaType

Period filter: this_month | q1_2026 | last_12_months | custom
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select, case, and_, extract, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import (
    Application,
    ApplicationTask,
    User,
    UserProfile,
    VisaType,
)
from app.schemas.attorney.analytics import (
    CaseloadMonthItem,
    CaseloadOverTimeResponse,
    CasesByVisaItem,
    CasesByVisaResponse,
    CaseStatusItem,
    CaseStatusResponse,
    KpiCardsResponse,
    UpcomingActionItem,
    UpcomingActionsResponse,
)


# ===========================================================================
# CONSTANTS
# ===========================================================================

_ACTIVE_STATUSES = ("in_progress", "action_needed", "rfe_response")
_CLOSED_STATUSES = ("approved", "rejected", "withdrawn")

# Color palette for status breakdown chart
_STATUS_META: dict[str, dict] = {
    "draft":         {"label": "Draft",         "color_hex": "#94A3B8"},
    "in_progress":   {"label": "In Progress",   "color_hex": "#3B82F6"},
    "action_needed": {"label": "Action Needed", "color_hex": "#F59E0B"},
    "rfe_response":  {"label": "RFE Response",  "color_hex": "#8B5CF6"},
    "submitted":     {"label": "Submitted",     "color_hex": "#06B6D4"},
    "approved":      {"label": "Approved",      "color_hex": "#22C55E"},
    "rejected":      {"label": "Rejected",      "color_hex": "#EF4444"},
    "withdrawn":     {"label": "Withdrawn",     "color_hex": "#6B7280"},
}

# Rotating color palette for visa type chart (cycles if more than 8 visa types)
_VISA_COLORS = [
    "#3B82F6", "#7C3AED", "#10B981", "#F59E0B",
    "#EF4444", "#06B6D4", "#EC4899", "#6B7280",
]


# ===========================================================================
# HELPERS
# ===========================================================================

def _date_range_for_period(
    period: str,
    date_from: Optional[str],
    date_to: Optional[str],
) -> tuple[datetime, datetime]:
    """
    Convert the period param into a (start, end) datetime pair (UTC).

    period values: this_month | q1_2026 | last_12_months | custom
    For 'custom', date_from and date_to must be provided as 'YYYY-MM-DD' strings.
    """
    now   = datetime.now(timezone.utc)
    today = now.date()

    if period == "this_month":
        start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
        end   = now

    elif period == "q1_2026":
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end   = datetime(2026, 3, 31, 23, 59, 59, tzinfo=timezone.utc)

    elif period == "last_12_months":
        start = datetime(today.year - 1, today.month, 1, tzinfo=timezone.utc)
        end   = now

    elif period == "custom":
        if not date_from or not date_to:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_from and date_to are required when period=custom.",
            )
        try:
            start = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
            end   = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_from and date_to must be YYYY-MM-DD format.",
            )
    else:
        # Default fallback — last 12 months
        start = datetime(today.year - 1, today.month, 1, tzinfo=timezone.utc)
        end   = now

    return start, end


def _round_pct(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total * 100, 1)


# ===========================================================================
# A. KPI CARDS
# ===========================================================================

async def get_kpi_cards(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    period: str,
    date_from: Optional[str],
    date_to: Optional[str],
) -> KpiCardsResponse:
    """
    Powers the 5 KPI stat cards.
    All queries are filtered to applications owned by the current attorney.
    """
    start, end = _date_range_for_period(period, date_from, date_to)
    now = datetime.now(timezone.utc)
    this_month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # 1. Active Cases — applications with an "active" status assigned to this attorney
    active_q = await db.execute(
        select(func.count(Application.id)).where(
            and_(
                Application.attorney_id == attorney_id,
                Application.status.in_(_ACTIVE_STATUSES),
            )
        )
    )
    active_cases = active_q.scalar() or 0

    # 2. New Clients This Month — users whose profile was created this calendar month
    #    and have at least one application assigned to this attorney
    new_clients_q = await db.execute(
        select(func.count(func.distinct(User.id))).where(
            and_(
                User.created_at >= this_month_start,
                User.id.in_(
                    select(Application.applicant_id).where(
                        Application.attorney_id == attorney_id
                    )
                ),
            )
        )
    )
    new_clients_month = new_clients_q.scalar() or 0

    # 3. Average Case Duration — avg days from created_at to submitted_at
    #    only for applications that have been submitted (not still in progress)
    avg_duration_q = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    Application.submitted_at - Application.created_at
                ) / 86400  # convert seconds → days
            )
        ).where(
            and_(
                Application.attorney_id == attorney_id,
                Application.submitted_at.isnot(None),
                Application.created_at >= start,
                Application.created_at <= end,
            )
        )
    )
    avg_raw = avg_duration_q.scalar()
    avg_case_duration_days = round(float(avg_raw), 1) if avg_raw else 0.0

    # 4. Pending Actions — tasks assigned to applications of this attorney
    #    that are not yet completed
    pending_q = await db.execute(
        select(func.count(ApplicationTask.id)).where(
            and_(
                ApplicationTask.application_id.in_(
                    select(Application.id).where(
                        Application.attorney_id == attorney_id
                    )
                ),
                ApplicationTask.status != "completed",
            )
        )
    )
    pending_actions = pending_q.scalar() or 0

    # 5. Monthly Revenue — not yet implemented; billing module is planned separately
    monthly_revenue = None

    return KpiCardsResponse(
        active_cases=active_cases,
        new_clients_month=new_clients_month,
        avg_case_duration_days=avg_case_duration_days,
        pending_actions=pending_actions,
        monthly_revenue=monthly_revenue,
    )


# ===========================================================================
# B. CASE STATUS BREAKDOWN
# ===========================================================================

async def get_case_status_breakdown(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    period: str,
    date_from: Optional[str],
    date_to: Optional[str],
) -> CaseStatusResponse:
    """
    Powers the Case Status Breakdown chart.
    Returns count + percentage per status for this attorney's cases.
    """
    start, end = _date_range_for_period(period, date_from, date_to)

    rows = await db.execute(
        select(Application.status, func.count(Application.id).label("cnt"))
        .where(
            and_(
                Application.attorney_id == attorney_id,
                Application.created_at >= start,
                Application.created_at <= end,
            )
        )
        .group_by(Application.status)
        .order_by(func.count(Application.id).desc())
    )
    rows = rows.all()

    total = sum(r.cnt for r in rows)

    items = [
        CaseStatusItem(
            status=r.status,
            label=_STATUS_META.get(r.status, {}).get("label", r.status.replace("_", " ").title()),
            count=r.cnt,
            percentage=_round_pct(r.cnt, total),
            color_hex=_STATUS_META.get(r.status, {}).get("color_hex", "#94A3B8"),
        )
        for r in rows
    ]

    return CaseStatusResponse(items=items, total=total)


# ===========================================================================
# C. CASES BY VISA TYPE
# ===========================================================================

async def get_cases_by_visa(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    period: str,
    date_from: Optional[str],
    date_to: Optional[str],
) -> CasesByVisaResponse:
    """
    Powers the Cases by Visa Type chart.
    Groups applications by visa_type and returns count + percentage.
    """
    start, end = _date_range_for_period(period, date_from, date_to)

    rows = await db.execute(
        select(
            VisaType.id,
            VisaType.code,
            VisaType.name,
            func.count(Application.id).label("cnt"),
        )
        .join(VisaType, Application.visa_type_id == VisaType.id)
        .where(
            and_(
                Application.attorney_id == attorney_id,
                Application.created_at >= start,
                Application.created_at <= end,
            )
        )
        .group_by(VisaType.id, VisaType.code, VisaType.name)
        .order_by(func.count(Application.id).desc())
    )
    rows = rows.all()

    total = sum(r.cnt for r in rows)

    items = [
        CasesByVisaItem(
            visa_type_id=r.id,
            visa_code=r.code,
            visa_name=r.name,
            count=r.cnt,
            percentage=_round_pct(r.cnt, total),
            color_hex=_VISA_COLORS[i % len(_VISA_COLORS)],
        )
        for i, r in enumerate(rows)
    ]

    return CasesByVisaResponse(items=items, total=total)


# ===========================================================================
# D. CASELOAD OVER TIME + CASE SUCCESS RATE
# ===========================================================================

async def get_caseload_over_time(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    period: str,
    date_from: Optional[str],
    date_to: Optional[str],
) -> CaseloadOverTimeResponse:
    """
    Powers the Caseload Over Time line chart AND the Case Success Rate card.

    Returns one data point per calendar month in the selected period.
    Also computes case_success_rate = approved / (approved + rejected + withdrawn) * 100.
    """
    start, end = _date_range_for_period(period, date_from, date_to)

    # Monthly active case counts grouped by year + month
    monthly_rows = await db.execute(
        select(
            extract("year",  Application.created_at).label("yr"),
            extract("month", Application.created_at).label("mo"),
            func.count(Application.id).label("cnt"),
        )
        .where(
            and_(
                Application.attorney_id == attorney_id,
                Application.created_at >= start,
                Application.created_at <= end,
            )
        )
        .group_by("yr", "mo")
        .order_by("yr", "mo")
    )
    monthly_rows = monthly_rows.all()

    month_labels = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }

    months = [
        CaseloadMonthItem(
            month=f"{int(r.yr):04d}-{int(r.mo):02d}",
            label=f"{month_labels[int(r.mo)]} {int(r.yr)}",
            active_cases=r.cnt,
        )
        for r in monthly_rows
    ]

    # Case success rate — approved / total closed
    closed_q = await db.execute(
        select(
            Application.status,
            func.count(Application.id).label("cnt"),
        )
        .where(
            and_(
                Application.attorney_id == attorney_id,
                Application.status.in_(_CLOSED_STATUSES),
                Application.created_at >= start,
                Application.created_at <= end,
            )
        )
        .group_by(Application.status)
    )
    closed_rows = closed_q.all()

    total_closed  = sum(r.cnt for r in closed_rows)
    total_approved = sum(r.cnt for r in closed_rows if r.status == "approved")
    success_rate   = _round_pct(total_approved, total_closed)

    return CaseloadOverTimeResponse(
        months=months,
        case_success_rate=success_rate,
        industry_avg_rate=79.0,
    )


# ===========================================================================
# E. UPCOMING ACTIONS TABLE
# ===========================================================================

async def get_upcoming_actions(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    limit: int,
    offset: int,
) -> UpcomingActionsResponse:
    """
    Powers the Upcoming Actions Required table.
    Returns tasks for this attorney's applications, ordered by due_date ASC.
    Includes overdue tasks at the top.
    """
    now = datetime.now(timezone.utc)

    # Base query — join ApplicationTask → Application → User → UserProfile → VisaType
    base = (
        select(
            ApplicationTask.id.label("task_id"),
            ApplicationTask.application_id,
            ApplicationTask.title.label("action_title"),
            ApplicationTask.due_date,
            ApplicationTask.priority,
            Application.case_number,
            Application.applicant_id.label("client_user_id"),
            VisaType.code.label("visa_code"),
            func.concat(UserProfile.first_name, " ", UserProfile.last_name).label("client_name"),
            UserProfile.avatar_url.label("client_avatar"),
        )
        .join(Application, ApplicationTask.application_id == Application.id)
        .join(VisaType, Application.visa_type_id == VisaType.id)
        .join(User, Application.applicant_id == User.id)
        .join(UserProfile, User.id == UserProfile.user_id)
        .where(
            and_(
                Application.attorney_id == attorney_id,
                ApplicationTask.status != "completed",
            )
        )
        .order_by(ApplicationTask.due_date.asc())
    )

    # Total count for pagination
    count_q = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = count_q.scalar() or 0

    # Paginated rows
    rows_q = await db.execute(base.limit(limit).offset(offset))
    rows   = rows_q.all()

    items = [
        UpcomingActionItem(
            task_id=r.task_id,
            application_id=r.application_id,
            client_user_id=r.client_user_id,
            client_name=r.client_name.strip(),
            client_avatar=r.client_avatar,
            case_number=r.case_number or f"#{r.visa_code}-{r.application_id.hex[:8].upper()}",
            visa_code=r.visa_code,
            action_title=r.action_title,
            due_date=r.due_date.date() if isinstance(r.due_date, datetime) else r.due_date,
            is_overdue=r.due_date < now if r.due_date else False,
            priority=r.priority or "medium",
        )
        for r in rows
    ]

    return UpcomingActionsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
