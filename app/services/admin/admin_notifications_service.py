"""
app/services/admin/admin_notifications_service.py

Section B spec — service layer for the admin cross-role notification feed.
Mirrors app/services/attorney/notifications_reminders_service.py with the
`user_id == current_user.id` predicate dropped (admin sees every user's
notifications, via the fan-out rows created by
app/services/shared/admin_notification_fanout.py), plus:

  - optional role_filter (hr|app_admin|employee|attorney|all — NATIVE role
    names, rename skipped) and user_id filters
  - triggered_by_* / recipient_* fields on each item (spec §B2)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import (
    Application,
    CalendarEvent,
    Notification,
    Role,
    User,
    UserRole,
    VisaType,
)
from app.schemas.admin.notifications_reminders import (
    AdminNotificationItem,
    AdminNotificationListResponse,
)
from app.schemas.attorney.notifications_reminders import (
    ReminderItemResponse,
    ReminderListResponse,
    TabCountsResponse,
)

_BADGE_LABELS: dict[str, str] = {
    "missing_document":    "Document Required",
    "deadline_approaching": "Urgent Deadline",
    "policy_update":       "Policy Update",
    "document_approved":   "Document Added",
    "case_status_updated": "Case Update",
    "participant_added":   "Participant Added",
    "document_comment":    "New Comment",
    "weekly_summary":      "Weekly Summary",
    "security_alert":      "Security Alert",
    "payment_receipt":     "Payment",
    "immigration_news":    "News",
    "task_assigned":       "Task Assigned",
    "document_requested":  "Document Requested",
    "document_request_fulfilled": "Document Fulfilled",
    "document_uploaded_by_staff": "Document Uploaded",
    "document_uploaded":   "Document Uploaded",
    "chat_message_received": "New Message",
    "deadline_missed":    "Deadline Missed",
    "calendar_event_reminder": "Reminder",
    "document_request_needs_hr_review": "Needs HR Review",
    "document_request_declined": "Request Declined",
    "document_needs_hr_release": "Needs HR Release",
    "document_release_declined": "Release Declined",
}


def _reminder_badge(minutes: int) -> str:
    if minutes <= 60:
        return "1-Hour Reminder"
    elif minutes <= 1440:
        return "1-Day Reminder"
    else:
        return "2-Day Reminder"


async def _role_for_user(db: AsyncSession, user_id: Optional[uuid.UUID]) -> Optional[str]:
    if not user_id:
        return None
    return (
        await db.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(UserRole.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _name_for_user(db: AsyncSession, user_id: Optional[uuid.UUID]) -> Optional[str]:
    if not user_id:
        return None
    row = (
        await db.execute(select(User.first_name, User.last_name).where(User.id == user_id))
    ).one_or_none()
    if not row:
        return None
    return f"{row.first_name} {row.last_name}".strip()


async def _enrich_admin_notification(
    db: AsyncSession,
    notification: Notification,
) -> AdminNotificationItem:
    client_name    = None
    visa_type_code = None
    case_reference = notification.case_reference

    if notification.application_id:
        result = await db.execute(
            select(
                User.first_name,
                User.last_name,
                VisaType.code,
                Application.application_number,
            )
            .join(Application, Application.id == notification.application_id)
            .join(User,     User.id     == Application.user_id)
            .join(VisaType, VisaType.id == Application.visa_type_id)
            .where(Application.id == notification.application_id)
        )
        row = result.one_or_none()
        if row:
            client_name    = f"{row.first_name} {row.last_name}".strip()
            visa_type_code = row.code
            case_reference = f"#{row.application_number}"

    badge_label = _BADGE_LABELS.get(notification.notification_type, notification.notification_type)
    if notification.notification_type == "deadline_approaching" and notification.priority != "urgent":
        badge_label = "Deadline"

    triggered_by_role = await _role_for_user(db, notification.actor_id)
    triggered_by_name = await _name_for_user(db, notification.actor_id) or notification.actor_label
    recipient_role    = await _role_for_user(db, notification.user_id)
    recipient_name    = await _name_for_user(db, notification.user_id)

    return AdminNotificationItem(
        id                = notification.id,
        notification_type = notification.notification_type,
        badge_label       = badge_label,
        category          = notification.category,
        priority          = notification.priority,
        title             = notification.title,
        body              = notification.body,
        client_name       = client_name,
        visa_type_code    = visa_type_code,
        case_reference    = case_reference,
        created_at        = notification.created_at,
        is_read           = notification.is_read,
        is_dismissed      = notification.is_dismissed,
        show_unread_dot   = not notification.is_read,
        triggered_by_user_id   = str(notification.actor_id) if notification.actor_id else None,
        triggered_by_user_name = triggered_by_name,
        triggered_by_role      = triggered_by_role,
        recipient_user_id      = str(notification.user_id),
        recipient_user_name    = recipient_name,
        recipient_role         = recipient_role,
    )


async def _enrich_reminder(db: AsyncSession, event: CalendarEvent) -> ReminderItemResponse:
    client_name    = None
    visa_type_code = None
    case_reference = None
    today          = datetime.now(timezone.utc).date()

    if event.application_id:
        result = await db.execute(
            select(
                User.first_name,
                User.last_name,
                VisaType.code,
                Application.application_number,
            )
            .join(Application, Application.id == event.application_id)
            .join(User,     User.id     == Application.user_id)
            .join(VisaType, VisaType.id == Application.visa_type_id)
            .where(Application.id == event.application_id)
        )
        row = result.one_or_none()
        if row:
            client_name    = f"{row.first_name} {row.last_name}".strip()
            visa_type_code = row.code
            case_reference = f"#{row.application_number}"

    return ReminderItemResponse(
        id               = event.id,
        title            = event.title,
        badge_label      = _reminder_badge(event.reminder_minutes),
        event_date       = event.event_date,
        start_time       = event.start_time,
        reminder_minutes = event.reminder_minutes,
        client_name      = client_name,
        visa_type_code   = visa_type_code,
        case_reference   = case_reference,
        is_upcoming      = event.event_date >= today,
        created_at       = event.created_at,
    )


def _apply_role_filter(stmt, role_filter: Optional[str]):
    """Joins Notification -> User -> UserRole -> Role and filters by
    NATIVE role name (hr | app_admin | employee | attorney)."""
    if not role_filter or role_filter == "all":
        return stmt
    return (
        stmt.join(User, User.id == Notification.user_id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.name == role_filter)
    )


async def get_tab_counts(
    db: AsyncSession,
    role_filter: Optional[str] = "all",
    user_id: Optional[uuid.UUID] = None,
) -> TabCountsResponse:
    today = datetime.now(timezone.utc).date()

    base = select(func.count(Notification.id)).where(Notification.is_dismissed == False)  # noqa: E712
    if user_id:
        base = base.where(Notification.user_id == user_id)
    base = _apply_role_filter(base, role_filter)

    all_updates_unread = (
        await db.execute(base.where(Notification.is_read == False))  # noqa: E712
    ).scalar() or 0

    deadlines_unread = (
        await db.execute(base.where(Notification.category == "deadline", Notification.is_read == False))  # noqa: E712
    ).scalar() or 0

    reminders_q = select(func.count(CalendarEvent.id)).where(
        and_(
            CalendarEvent.reminder_enabled == True,   # noqa: E712
            CalendarEvent.event_date       >= today,
            CalendarEvent.status           != "cancelled",
        )
    )
    if user_id:
        reminders_q = reminders_q.where(CalendarEvent.attorney_id == user_id)
    reminders_total = (await db.execute(reminders_q)).scalar() or 0

    return TabCountsResponse(
        all_updates_unread = all_updates_unread,
        reminders_total    = reminders_total,
        deadlines_unread   = deadlines_unread,
    )


async def list_updates(
    db: AsyncSession,
    role_filter: Optional[str] = "all",
    user_id: Optional[uuid.UUID] = None,
    before: Optional[datetime] = None,
    limit: int = 20,
) -> AdminNotificationListResponse:
    query = select(Notification).where(Notification.is_dismissed == False)  # noqa: E712
    if user_id:
        query = query.where(Notification.user_id == user_id)
    query = _apply_role_filter(query, role_filter)
    if before:
        query = query.where(Notification.created_at < before)
    query = query.order_by(Notification.created_at.desc()).limit(limit + 1)

    notifications = (await db.execute(query)).scalars().all()
    has_more    = len(notifications) > limit
    items_slice = notifications[:limit]
    next_cursor = items_slice[-1].created_at.isoformat() if has_more and items_slice else None

    unread_stmt = select(func.count(Notification.id)).where(
        Notification.is_read == False, Notification.is_dismissed == False,  # noqa: E712
    )
    if user_id:
        unread_stmt = unread_stmt.where(Notification.user_id == user_id)
    unread_stmt = _apply_role_filter(unread_stmt, role_filter)
    total_unread = (await db.execute(unread_stmt)).scalar() or 0

    items = [await _enrich_admin_notification(db, n) for n in items_slice]

    return AdminNotificationListResponse(
        items=items, total_unread=total_unread, has_more=has_more, next_cursor=next_cursor,
    )


async def list_deadlines(
    db: AsyncSession,
    role_filter: Optional[str] = "all",
    user_id: Optional[uuid.UUID] = None,
    before: Optional[datetime] = None,
    limit: int = 20,
) -> AdminNotificationListResponse:
    query = select(Notification).where(
        Notification.category == "deadline", Notification.is_dismissed == False,  # noqa: E712
    )
    if user_id:
        query = query.where(Notification.user_id == user_id)
    query = _apply_role_filter(query, role_filter)
    if before:
        query = query.where(Notification.created_at < before)
    query = query.order_by(Notification.created_at.desc()).limit(limit + 1)

    notifications = (await db.execute(query)).scalars().all()
    has_more    = len(notifications) > limit
    items_slice = notifications[:limit]
    next_cursor = items_slice[-1].created_at.isoformat() if has_more and items_slice else None

    unread_stmt = select(func.count(Notification.id)).where(
        Notification.category == "deadline",
        Notification.is_read == False, Notification.is_dismissed == False,  # noqa: E712
    )
    if user_id:
        unread_stmt = unread_stmt.where(Notification.user_id == user_id)
    unread_stmt = _apply_role_filter(unread_stmt, role_filter)
    total_unread = (await db.execute(unread_stmt)).scalar() or 0

    items = [await _enrich_admin_notification(db, n) for n in items_slice]

    return AdminNotificationListResponse(
        items=items, total_unread=total_unread, has_more=has_more, next_cursor=next_cursor,
    )


async def list_reminders(
    db: AsyncSession,
    user_id: Optional[uuid.UUID] = None,
    before: Optional[datetime] = None,
    limit: int = 20,
    include_past: bool = False,
) -> ReminderListResponse:
    """Cross-role reminders feed. CalendarEvent is only ever owned by an
    attorney (attorney_id column) in this schema, so 'all roles' in
    practice means 'all attorneys' unless user_id narrows it."""
    today = datetime.now(timezone.utc).date()

    query = select(CalendarEvent).where(
        and_(
            CalendarEvent.reminder_enabled == True,   # noqa: E712
            CalendarEvent.status           != "cancelled",
        )
    )
    if user_id:
        query = query.where(CalendarEvent.attorney_id == user_id)

    if not include_past:
        query = query.where(CalendarEvent.event_date >= today)
    elif before:
        query = query.where(CalendarEvent.created_at < before)

    query = query.order_by(
        CalendarEvent.event_date.asc() if not include_past else CalendarEvent.created_at.desc()
    ).limit(limit + 1)

    events = (await db.execute(query)).scalars().all()
    has_more    = len(events) > limit
    items_slice = events[:limit]
    next_cursor = items_slice[-1].created_at.isoformat() if has_more and items_slice else None

    total_stmt = select(func.count(CalendarEvent.id)).where(
        and_(
            CalendarEvent.reminder_enabled == True,   # noqa: E712
            CalendarEvent.event_date       >= today,
            CalendarEvent.status           != "cancelled",
        )
    )
    if user_id:
        total_stmt = total_stmt.where(CalendarEvent.attorney_id == user_id)
    total = (await db.execute(total_stmt)).scalar() or 0

    items = [await _enrich_reminder(db, e) for e in items_slice]

    return ReminderListResponse(items=items, total=total, has_more=has_more, next_cursor=next_cursor)


async def mark_all_read(
    db: AsyncSession,
    category: Optional[str] = None,
    role_filter: Optional[str] = "all",
    user_id: Optional[uuid.UUID] = None,
) -> dict:
    from sqlalchemy import update

    now = datetime.now(timezone.utc)
    where = [Notification.is_read == False]  # noqa: E712
    if category:
        where.append(Notification.category == category)
    if user_id:
        where.append(Notification.user_id == user_id)

    stmt = update(Notification).where(and_(*where)).values(is_read=True, read_at=now)

    if role_filter and role_filter != "all":
        scoped_ids = (
            await db.execute(
                select(Notification.id)
                .join(User, User.id == Notification.user_id)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(Role.name == role_filter, and_(*where))
            )
        ).scalars().all()
        stmt = update(Notification).where(Notification.id.in_(scoped_ids)).values(is_read=True, read_at=now)

    await db.execute(stmt)
    await db.commit()
    return {"message": "All notifications marked as read."}
