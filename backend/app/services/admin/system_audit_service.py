"""
app/services/system_audit_service.py — Fixed to match actual AuditLog columns.

Actual AuditLog columns:
  id, actor_id, actor_type, actor_email, actor_role_snapshot,
  action, resource_type, resource_id, old_value, new_value,
  description, ip_address, user_agent, session_id, severity, created_at

Removed (did not exist): event_type, security_event_type, resource, extra_metadata

Mapping applied:
  event_type          → derived from action prefix  (e.g. "user.*" → "user_login")
  security_event_type → derived from action value   (e.g. "failed_login")
  resource            → resource_type
  extra_metadata      → description (JSON string fallback)
"""
from __future__ import annotations

import csv
import io
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import AuditLog, Role, User, UserLoginHistory, UserRole
from app.schemas.admin.system_audit import (
    ActivityTimelineResponse,
    AuditDashboardFullResponse,
    AuditDashboardKPIResponse,
    AuditKPICard,
    AuditLogListResponse,
    AuditLogRow,
    EventTypeDistributionResponse,
    EventTypeSlice,
    SecurityEventSlice,
    SecurityEventsResponse,
    TimelineDataPoint,
    TimelinePeriod,
    TopUserActivitiesResponse,
    TopUserActivity,
)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

# Maps action prefixes / values → event_type bucket
def _derive_event_type(action: str) -> str:
    if not action:
        return "other"
    a = action.lower()
    if a.startswith("user.login") or a in ("login_success", "login_failed", "login_blocked"):
        return "user_login"
    if a.startswith("document") or "document" in a:
        return "document_action"
    if a.startswith("application") or a.startswith("task") or a.startswith("profile") or a.startswith("setting"):
        return "data_update"
    if a.startswith("suspicious") or "password_reset" in a or "permission" in a or "account_suspended" in a or "failed_login" in a or "blocked_login" in a:
        return "security_event"
    if a.startswith("subscription") or a.startswith("payment") or a.startswith("visa_type") or a.startswith("maintenance") or a.startswith("feature"):
        return "system_action"
    return "other"


# Maps action value → security_event_type bucket
SECURITY_ACTIONS = {
    "login_failed":              "failed_login",
    "login_blocked":             "blocked_login",
    "suspicious_access_detected":"suspicious_access",
    "password_reset_requested":  "password_reset",
    "password_reset_completed":  "password_reset",
    "permission_assigned":       "permission_change",
    "permission_removed":        "permission_change",
    "account_suspended":         "account_suspended",
}

EVENT_TYPE_LABELS = {
    "user_login":      "User Login",
    "document_action": "Document Upload",
    "data_update":     "Data Update",
    "security_event":  "Security Event",
    "system_action":   "System Action",
    "other":           "Other",
}

ACTION_LABELS = {
    "document_uploaded":          "Document Uploaded",
    "document_verified":          "Document Verified",
    "document_rejected":          "Document Rejected",
    "document_downloaded":        "Document Downloaded",
    "document_version_updated":   "Document Version Updated",
    "ocr_completed":              "OCR Completed",
    "application_created":        "Application Created",
    "application_status_changed": "Application Status Changed",
    "application_deleted":        "Application Deleted",
    "task_completed":             "Task Completed",
    "profile_updated":            "Profile Updated",
    "onboarding_completed":       "Onboarding Completed",
    "visa_type_created":          "Visa Type Created",
    "visa_type_updated":          "Visa Type Updated",
    "setting_updated":            "Setting Updated",
    "feature_toggled":            "Feature Flag Toggled",
    "maintenance_toggled":        "Maintenance Mode Toggled",
    "permission_assigned":        "Permission Assigned",
    "permission_removed":         "Permission Removed",
    "role_assigned":              "Role Assigned",
    "role_removed":               "Role Removed",
    "account_suspended":          "Account Suspended",
    "account_activated":          "Account Activated",
    "account_deleted":            "Account Deleted",
    "password_reset_requested":   "Password Reset Requested",
    "password_reset_completed":   "Password Reset Completed",
    "suspicious_access_detected": "Suspicious Access Detected",
    "subscription_created":       "Subscription Created",
    "subscription_upgraded":      "Subscription Upgraded",
    "subscription_downgraded":    "Subscription Downgraded",
    "subscription_cancelled":     "Subscription Cancelled",
    "payment_succeeded":          "Payment Succeeded",
    "payment_failed":             "Payment Failed",
    "support_ticket_created":     "Support Ticket Created",
    "support_ticket_replied":     "Support Ticket Replied",
    "support_ticket_closed":      "Support Ticket Closed",
    "coupon_applied":             "Coupon Applied",
}

SECURITY_EVENT_LABELS = {
    "failed_login":      "Failed Login",
    "blocked_login":     "Blocked Login",
    "suspicious_access": "Suspicious Access",
    "password_reset":    "Password Reset",
    "permission_change": "Permission Change",
    "account_suspended": "Account Suspended",
}

EVENT_TYPE_COLORS = {
    "user_login":      "#4CAF50",
    "document_action": "#2196F3",
    "data_update":     "#FF9800",
    "security_event":  "#F44336",
    "system_action":   "#9C27B0",
    "other":           "#607D8B",
}

SECURITY_EVENT_COLORS = {
    "failed_login":      "#F44336",
    "blocked_login":     "#FF5722",
    "suspicious_access": "#FF9800",
    "password_reset":    "#FFC107",
    "permission_change": "#9C27B0",
    "account_suspended": "#795548",
}

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _period_start(period: TimelinePeriod, year: Optional[int], month: Optional[int]) -> datetime:
    now   = datetime.now(timezone.utc)
    today = now.date()
    if period == "7days":
        return datetime.combine(today - timedelta(days=6), datetime.min.time()).replace(tzinfo=timezone.utc)
    if period == "30days":
        return datetime.combine(today - timedelta(days=29), datetime.min.time()).replace(tzinfo=timezone.utc)
    if period == "month":
        return datetime(year or today.year, month or today.month, 1, tzinfo=timezone.utc)
    if period == "year":
        return datetime(year or today.year, 1, 1, tzinfo=timezone.utc)
    return datetime.combine(today - timedelta(days=6), datetime.min.time()).replace(tzinfo=timezone.utc)


def _delta(current: int, previous: int) -> tuple[str, bool]:
    if previous == 0:
        return ("N/A", True)
    pct  = ((current - previous) / previous) * 100
    sign = "+" if pct >= 0 else ""
    return (f"{sign}{pct:.1f}% vs yesterday", pct >= 0)


def _initials(name: str) -> str:
    parts = name.strip().split()
    return name[:2].upper() if len(parts) == 1 else (parts[0][0] + parts[1][0]).upper()


# ─────────────────────────────────────────────
# Core helper — call from any service to log an event
# ─────────────────────────────────────────────

async def log_audit_event(
    db:          AsyncSession,
    action:      str,
    actor_id:    Optional[UUID] = None,
    actor_type:  str = "user",
    actor_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id:   Optional[str] = None,
    description:   Optional[str] = None,
    ip_address:    Optional[str] = None,
    severity:      str = "info",
) -> None:
    """
    Drop-in logger. Uses only actual AuditLog columns.
    severity: "info" | "warning" | "critical"
    """
    db.add(AuditLog(
        actor_id      = actor_id,
        actor_type    = actor_type,
        actor_email   = actor_email,
        action        = action,
        resource_type = resource_type,
        resource_id   = resource_id,
        description   = description,
        ip_address    = ip_address,
        severity      = severity,
    ))
    # caller does the commit


# ─────────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────────

async def service_get_audit_kpis(db: AsyncSession) -> AuditDashboardKPIResponse:
    now  = datetime.now(timezone.utc)
    h24  = now - timedelta(hours=24)
    h48  = now - timedelta(hours=48)
    d7   = now - timedelta(days=7)
    d14  = now - timedelta(days=14)

    async def _count(model, *filters):
        return int((await db.execute(select(func.count(model.id)).where(*filters))).scalar() or 0)

    total_now  = await _count(AuditLog, AuditLog.created_at >= h24)
    total_prev = await _count(AuditLog, AuditLog.created_at >= h48, AuditLog.created_at < h24)

    # Security events = severity warning or critical
    sec_now  = await _count(AuditLog, AuditLog.created_at >= d7,  AuditLog.severity.in_(["warning", "critical"]))
    sec_prev = await _count(AuditLog, AuditLog.created_at >= d14, AuditLog.created_at < d7, AuditLog.severity.in_(["warning", "critical"]))

    # Active users = distinct actors in last 24h
    active_now  = int((await db.execute(
        select(func.count(func.distinct(AuditLog.actor_id))).where(AuditLog.created_at >= h24, AuditLog.actor_id.isnot(None))
    )).scalar() or 0)
    active_prev = int((await db.execute(
        select(func.count(func.distinct(AuditLog.actor_id))).where(AuditLog.created_at >= h48, AuditLog.created_at < h24, AuditLog.actor_id.isnot(None))
    )).scalar() or 0)

    # Failed logins from UserLoginHistory
    fail_now  = await _count(UserLoginHistory, UserLoginHistory.created_at >= h24,  UserLoginHistory.status == "failed")
    fail_prev = await _count(UserLoginHistory, UserLoginHistory.created_at >= h48,  UserLoginHistory.created_at < h24, UserLoginHistory.status == "failed")

    t_delta, t_pos = _delta(total_now,  total_prev)
    s_delta, s_pos = _delta(sec_now,    sec_prev)
    a_delta, a_pos = _delta(active_now, active_prev)
    f_delta, f_pos = _delta(fail_now,   fail_prev)

    return AuditDashboardKPIResponse(
        total_events    = AuditKPICard(value_display=str(total_now),  delta_display=t_delta, delta_positive=t_pos,     period_label="Last 24 Hours"),
        security_events = AuditKPICard(value_display=str(sec_now),    delta_display=s_delta, delta_positive=not s_pos, period_label="Last 7 Days"),
        active_users    = AuditKPICard(value_display=str(active_now), delta_display=a_delta, delta_positive=a_pos,     period_label="Last 24 Hours"),
        failed_logins   = AuditKPICard(value_display=str(fail_now),   delta_display=f_delta, delta_positive=not f_pos, period_label="Last 24 Hours"),
    )


# ─────────────────────────────────────────────
# Activity Timeline
# ─────────────────────────────────────────────

async def service_get_activity_timeline(
    db: AsyncSession, period: TimelinePeriod = "7days",
    year: Optional[int] = None, month: Optional[int] = None,
) -> ActivityTimelineResponse:
    start = _period_start(period, year, month)

    res = await db.execute(
        select(func.date(AuditLog.created_at).label("d"), func.count(AuditLog.id).label("c"))
        .where(AuditLog.created_at >= start)
        .group_by(func.date(AuditLog.created_at))
        .order_by(func.date(AuditLog.created_at))
    )

    login_res = await db.execute(
        select(func.date(UserLoginHistory.created_at).label("d"), func.count(UserLoginHistory.id).label("c"))
        .where(UserLoginHistory.created_at >= start)
        .group_by(func.date(UserLoginHistory.created_at))
    )
    login_by_day = {str(r.d): int(r.c) for r in login_res.all()}

    points = []
    for r in res.all():
        day_str = str(r.d)
        total   = int(r.c) + login_by_day.get(day_str, 0)
        points.append(TimelineDataPoint(date=day_str, event_count=total, login_count=login_by_day.get(day_str, 0)))

    return ActivityTimelineResponse(data_points=points, period=period)


# ─────────────────────────────────────────────
# Event Type Distribution
# ─────────────────────────────────────────────

async def service_get_event_type_distribution(
    db: AsyncSession, period: TimelinePeriod = "7days",
    year: Optional[int] = None, month: Optional[int] = None,
) -> EventTypeDistributionResponse:
    start = _period_start(period, year, month)

    # Pull all actions and bucket them in Python
    res = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id).label("c"))
        .where(AuditLog.created_at >= start)
        .group_by(AuditLog.action)
    )
    counts: dict[str, int] = {}
    for r in res.all():
        et = _derive_event_type(r.action)
        counts[et] = counts.get(et, 0) + int(r.c)

    # Add login history
    login_cnt = int((await db.execute(
        select(func.count(UserLoginHistory.id)).where(UserLoginHistory.created_at >= start)
    )).scalar() or 0)
    counts["user_login"] = counts.get("user_login", 0) + login_cnt

    total  = sum(counts.values()) or 1
    slices = [
        EventTypeSlice(
            event_type  = et,
            label       = EVENT_TYPE_LABELS.get(et, et),
            count       = cnt,
            percentage  = round(cnt / total * 100, 1),
            color       = EVENT_TYPE_COLORS.get(et, "#607D8B"),
        )
        for et, cnt in sorted(counts.items(), key=lambda x: -x[1]) if cnt > 0
    ]
    return EventTypeDistributionResponse(slices=slices, total_events=sum(counts.values()), period=period)


# ─────────────────────────────────────────────
# Top User Activities
# ─────────────────────────────────────────────

async def service_get_top_user_activities(
    db: AsyncSession, period: TimelinePeriod = "7days", role_filter: str = "all",
    year: Optional[int] = None, month: Optional[int] = None, limit: int = 10,
) -> TopUserActivitiesResponse:
    start = _period_start(period, year, month)

    res = await db.execute(
        select(AuditLog.actor_id, func.count(AuditLog.id).label("cnt"), func.max(AuditLog.created_at).label("last"))
        .where(AuditLog.created_at >= start, AuditLog.actor_id.isnot(None))
        .group_by(AuditLog.actor_id).order_by(desc("cnt")).limit(limit * 3)
    )
    rows = res.all()

    out = []
    for row in rows:
        if len(out) >= limit:
            break
        user = (await db.execute(select(User).where(User.id == row.actor_id))).scalar_one_or_none()
        if not user:
            continue

        role_name = (await db.execute(
            select(Role.name).join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == row.actor_id).limit(1)
        )).scalar_one_or_none() or "unknown"

        if role_filter != "all" and role_name != role_filter:
            continue

        name = f"{user.first_name} {user.last_name}".strip() or "Unknown"
        out.append(TopUserActivity(
            user_id        = user.id,
            user_name      = name,
            user_email     = user.email,
            avatar_initials= _initials(name),
            role           = role_name,
            action_count   = int(row.cnt),
            last_action_at = row.last,
        ))

    return TopUserActivitiesResponse(users=out, period=period, role_filter=role_filter, total_users=len(out))


# ─────────────────────────────────────────────
# Security Events
# ─────────────────────────────────────────────

async def service_get_security_events(
    db: AsyncSession, period: TimelinePeriod = "7days",
    year: Optional[int] = None, month: Optional[int] = None,
) -> SecurityEventsResponse:
    start = _period_start(period, year, month)

    # Security events = severity warning/critical OR known security actions
    res = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id).label("c"))
        .where(
            AuditLog.created_at >= start,
            AuditLog.severity.in_(["warning", "critical"])
        )
        .group_by(AuditLog.action)
    )
    counts: dict[str, int] = {}
    for r in res.all():
        sec_type = SECURITY_ACTIONS.get(r.action, "suspicious_access")
        counts[sec_type] = counts.get(sec_type, 0) + int(r.c)

    # Add failed/blocked logins from UserLoginHistory
    login_res = await db.execute(
        select(UserLoginHistory.status, func.count(UserLoginHistory.id).label("c"))
        .where(UserLoginHistory.created_at >= start, UserLoginHistory.status.in_(["failed", "blocked"]))
        .group_by(UserLoginHistory.status)
    )
    for r in login_res.all():
        k = "failed_login" if r.status == "failed" else "blocked_login"
        counts[k] = counts.get(k, 0) + int(r.c)

    # Suspicious logins
    suspicious = int((await db.execute(
        select(func.count(UserLoginHistory.id))
        .where(UserLoginHistory.created_at >= start, UserLoginHistory.is_suspicious == True)
    )).scalar() or 0)
    if suspicious:
        counts["suspicious_access"] = counts.get("suspicious_access", 0) + suspicious

    total  = sum(counts.values()) or 1
    slices = [
        SecurityEventSlice(
            security_event_type = et,
            label               = SECURITY_EVENT_LABELS.get(et, et),
            count               = cnt,
            percentage          = round(cnt / total * 100, 1),
            color               = SECURITY_EVENT_COLORS.get(et, "#607D8B"),
        )
        for et, cnt in sorted(counts.items(), key=lambda x: -x[1]) if cnt > 0
    ]
    return SecurityEventsResponse(slices=slices, total_count=sum(counts.values()), period=period)


# ─────────────────────────────────────────────
# Audit Log List
# ─────────────────────────────────────────────

async def service_list_audit_logs(
    db: AsyncSession, page: int = 1, page_size: int = 20,
    event_type: Optional[str] = None, action: Optional[str] = None,
    actor_id: Optional[UUID] = None, period: TimelinePeriod = "7days",
    year: Optional[int] = None, month: Optional[int] = None,
) -> AuditLogListResponse:
    start = _period_start(period, year, month)

    q = select(AuditLog).where(AuditLog.created_at >= start).order_by(desc(AuditLog.created_at))

    # event_type is now derived — filter by severity or action pattern
    if event_type == "security_event":
        q = q.where(AuditLog.severity.in_(["warning", "critical"]))
    elif event_type == "user_login":
        q = q.where(AuditLog.action.in_(["login_success", "login_failed", "login_blocked"]))
    elif event_type and event_type != "other":
        # best-effort: filter by action prefix matching the bucket
        q = q.where(AuditLog.action.ilike(f"{event_type.split('_')[0]}%"))

    if action:   q = q.where(AuditLog.action == action)
    if actor_id: q = q.where(AuditLog.actor_id == actor_id)

    total = int((await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
    logs  = (await db.execute(q.limit(page_size).offset((page - 1) * page_size))).scalars().all()

    items = []
    for log in logs:
        actor_name = actor_email = actor_role = None
        if log.actor_id:
            u = (await db.execute(select(User).where(User.id == log.actor_id))).scalar_one_or_none()
            if u:
                actor_name  = f"{u.first_name} {u.last_name}".strip()
                actor_email = u.email
                actor_role  = (await db.execute(
                    select(Role.name).join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == log.actor_id).limit(1)
                )).scalar_one_or_none()
        else:
            actor_name = "System"

        derived_event_type    = _derive_event_type(log.action)
        derived_security_type = SECURITY_ACTIONS.get(log.action)

        items.append(AuditLogRow(
            id                  = log.id,
            actor_id            = log.actor_id,
            actor_name          = actor_name,
            actor_email         = actor_email,
            actor_type          = log.actor_type,
            actor_role          = actor_role,
            event_type          = derived_event_type,
            event_type_label    = EVENT_TYPE_LABELS.get(derived_event_type, derived_event_type),
            action              = log.action,
            action_label        = ACTION_LABELS.get(log.action, log.action.replace("_", " ").title()),
            resource            = log.resource_type,       # ← mapped from resource_type
            resource_id         = str(log.resource_id) if log.resource_id else None,
            description         = log.description,
            security_event_type = derived_security_type,
            ip_address          = log.ip_address,
            extra_metadata      = None,                    # column removed
            created_at          = log.created_at,
        ))

    return AuditLogListResponse(
        items=items, total=total, page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


# ─────────────────────────────────────────────
# Export CSV
# ─────────────────────────────────────────────

async def service_export_audit_logs(
    db: AsyncSession, period: TimelinePeriod = "7days",
    year: Optional[int] = None, month: Optional[int] = None,
    event_type: Optional[str] = None,
) -> str:
    result = await service_list_audit_logs(
        db, page=1, page_size=10000,
        event_type=event_type, period=period, year=year, month=month,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Timestamp", "Actor", "Email", "Role", "Actor Type",
        "Event Type", "Action", "Resource", "Resource ID",
        "Description", "Security Event Type", "IP Address",
    ])
    for log in result.items:
        writer.writerow([
            log.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            log.actor_name or "System", log.actor_email or "",
            log.actor_role or "", log.actor_type,
            log.event_type_label, log.action_label,
            log.resource or "", log.resource_id or "",
            log.description or "", log.security_event_type or "",
            log.ip_address or "",
        ])
    return output.getvalue()


# ─────────────────────────────────────────────
# Full Dashboard
# ─────────────────────────────────────────────

async def service_get_full_audit_dashboard(
    db: AsyncSession, period: TimelinePeriod = "7days",
    year: Optional[int] = None, month: Optional[int] = None,
) -> AuditDashboardFullResponse:
    return AuditDashboardFullResponse(
        kpi          = await service_get_audit_kpis(db),
        timeline     = await service_get_activity_timeline(db, period, year, month),
        event_types  = await service_get_event_type_distribution(db, period, year, month),
        top_users    = await service_get_top_user_activities(db, period, year=year, month=month),
        security     = await service_get_security_events(db, period, year, month),
        generated_at = datetime.now(timezone.utc),
    )
