"""
notifications_reminders_service.py — Service layer for Notifications & Reminders (Screen 24).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.visamodels import (
    Application,
    CalendarEvent,
    Notification,
    User,
    VisaType,
)
from app.schemas.attorney.notifications_reminders import (
    NotificationItemResponse,
    NotificationListResponse,
    ReminderItemResponse,
    ReminderListResponse,
    TabCountsResponse,
)


# ===========================================================================
# CONSTANTS
# ===========================================================================

# Maps notification_type → badge label shown on Screen 24 card
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
}

# Maps reminder_minutes → badge label on Reminders tab
def _reminder_badge(minutes: int) -> str:
    if minutes <= 60:
        return "1-Hour Reminder"
    elif minutes <= 1440:
        return "1-Day Reminder"
    else:
        return "2-Day Reminder"


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

async def _enrich_notification(
    db:           AsyncSession,
    notification: Notification,
) -> NotificationItemResponse:
    """
    Enriches a Notification with client name, visa_type_code, case_reference
    derived from the linked application.

    Shown as: "John Doe - H-1B  •  #VF-2026-089"
    """
    client_name    = None
    visa_type_code = None
    case_reference = notification.case_reference   # use stored value as fallback

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

    # Override badge for deadline+urgent combo → "Urgent Deadline"
    badge_label = _BADGE_LABELS.get(notification.notification_type, notification.notification_type)
    if notification.notification_type == "deadline_approaching" and notification.priority != "urgent":
        badge_label = "Deadline"

    return NotificationItemResponse(
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
    )


async def _enrich_reminder(
    db:    AsyncSession,
    event: CalendarEvent,
) -> ReminderItemResponse:
    """
    Enriches a CalendarEvent (reminder) with client name, visa_type_code,
    case_reference from the linked application.
    """
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


# ===========================================================================
# A. TAB COUNTS
# ===========================================================================

async def get_tab_counts(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
) -> TabCountsResponse:
    """
    Powers the badge numbers on the 3 tabs.
    All Updates (12) | Reminders | Deadlines (3)
    """
    today = datetime.now(timezone.utc).date()

    # All Updates unread count — all unread, non-dismissed notifications
    unread_q = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id     == attorney_id,
                Notification.is_read     == False,     # noqa: E712
                Notification.is_dismissed == False,    # noqa: E712
            )
        )
    )
    all_updates_unread = unread_q.scalar() or 0

    # Deadlines unread — category=deadline + unread
    deadlines_q = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id      == attorney_id,
                Notification.category     == "deadline",
                Notification.is_read      == False,    # noqa: E712
                Notification.is_dismissed == False,    # noqa: E712
            )
        )
    )
    deadlines_unread = deadlines_q.scalar() or 0

    # Reminders total — upcoming calendar events with reminder_enabled=True
    reminders_q = await db.execute(
        select(func.count(CalendarEvent.id)).where(
            and_(
                CalendarEvent.attorney_id      == attorney_id,
                CalendarEvent.reminder_enabled == True,   # noqa: E712
                CalendarEvent.event_date       >= today,
                CalendarEvent.status           != "cancelled",
            )
        )
    )
    reminders_total = reminders_q.scalar() or 0

    return TabCountsResponse(
        all_updates_unread = all_updates_unread,
        reminders_total    = reminders_total,
        deadlines_unread   = deadlines_unread,
    )


# ===========================================================================
# B. ALL UPDATES TAB
# ===========================================================================

async def list_updates(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    before:      Optional[datetime] = None,   # cursor for "Load Older" button
    limit:       int                = 20,
) -> NotificationListResponse:
    """
    All Updates tab — all non-dismissed notifications newest first.
    Cursor-based pagination via `before` (created_at of last item seen).
    Powers "Load Older Notifications" button.
    """
    query = select(Notification).where(
        and_(
            Notification.user_id      == attorney_id,
            Notification.is_dismissed == False,        # noqa: E712
        )
    )

    if before:
        query = query.where(Notification.created_at < before)

    query = query.order_by(Notification.created_at.desc()).limit(limit + 1)

    result        = await db.execute(query)
    notifications = result.scalars().all()

    has_more    = len(notifications) > limit
    items_slice = notifications[:limit]
    next_cursor = items_slice[-1].created_at if has_more and items_slice else None

    # Unread count across all (not just this page)
    unread_q = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id      == attorney_id,
                Notification.is_read      == False,    # noqa: E712
                Notification.is_dismissed == False,    # noqa: E712
            )
        )
    )
    total_unread = unread_q.scalar() or 0

    items = [await _enrich_notification(db, n) for n in items_slice]

    return NotificationListResponse(
        items        = items,
        total_unread = total_unread,
        has_more     = has_more,
        next_cursor  = next_cursor,
    )


# ===========================================================================
# C. DEADLINES TAB
# ===========================================================================

async def list_deadlines(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    before:      Optional[datetime] = None,
    limit:       int                = 20,
) -> NotificationListResponse:
    """
    Deadlines tab — notifications with category='deadline', newest first.
    Same cursor pagination as All Updates.
    """
    query = select(Notification).where(
        and_(
            Notification.user_id      == attorney_id,
            Notification.category     == "deadline",
            Notification.is_dismissed == False,        # noqa: E712
        )
    )

    if before:
        query = query.where(Notification.created_at < before)

    query = query.order_by(Notification.created_at.desc()).limit(limit + 1)

    result        = await db.execute(query)
    notifications = result.scalars().all()

    has_more    = len(notifications) > limit
    items_slice = notifications[:limit]
    next_cursor = items_slice[-1].created_at if has_more and items_slice else None

    unread_q = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id      == attorney_id,
                Notification.category     == "deadline",
                Notification.is_read      == False,    # noqa: E712
                Notification.is_dismissed == False,    # noqa: E712
            )
        )
    )
    total_unread = unread_q.scalar() or 0

    items = [await _enrich_notification(db, n) for n in items_slice]

    return NotificationListResponse(
        items        = items,
        total_unread = total_unread,
        has_more     = has_more,
        next_cursor  = next_cursor,
    )


# ===========================================================================
# D. REMINDERS TAB
# ===========================================================================

async def list_reminders(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    before:      Optional[datetime] = None,
    limit:       int                = 20,
    include_past: bool              = False,
) -> ReminderListResponse:
    """
    Reminders tab — calendar_events WHERE reminder_enabled=TRUE for this attorney.
    Ordered by event_date ASC (upcoming first), then created_at DESC for past.

    Option A: queries existing calendar_events table — no new table needed.

    include_past=False → upcoming reminders (default on page load)
    include_past=True  → "Load Older" button fetches past reminders
    """
    today = datetime.now(timezone.utc).date()

    query = select(CalendarEvent).where(
        and_(
            CalendarEvent.attorney_id      == attorney_id,
            CalendarEvent.reminder_enabled == True,    # noqa: E712
            CalendarEvent.status           != "cancelled",
        )
    )

    if not include_past:
        query = query.where(CalendarEvent.event_date >= today)
    elif before:
        # cursor for loading older past reminders
        query = query.where(CalendarEvent.created_at < before)

    # Upcoming: soonest first. Past: newest first
    if not include_past:
        query = query.order_by(CalendarEvent.event_date.asc())
    else:
        query = query.order_by(CalendarEvent.created_at.desc())

    query = query.limit(limit + 1)

    result = await db.execute(query)
    events = result.scalars().all()

    has_more    = len(events) > limit
    items_slice = events[:limit]
    next_cursor = items_slice[-1].created_at if has_more and items_slice else None

    # Total upcoming reminders count (for tab badge)
    total_q = await db.execute(
        select(func.count(CalendarEvent.id)).where(
            and_(
                CalendarEvent.attorney_id      == attorney_id,
                CalendarEvent.reminder_enabled == True,   # noqa: E712
                CalendarEvent.event_date       >= today,
                CalendarEvent.status           != "cancelled",
            )
        )
    )
    total = total_q.scalar() or 0

    items = [await _enrich_reminder(db, e) for e in items_slice]

    return ReminderListResponse(
        items       = items,
        total       = total,
        has_more    = has_more,
        next_cursor = next_cursor,
    )


# ===========================================================================
# E. MARK ALL AS READ
# ===========================================================================

async def mark_all_read(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    category:    Optional[str] = None,
) -> dict:
    """
    "Mark All as Read" button — marks all unread notifications as read.
    Optionally scoped to a category (e.g. category="deadline" for Deadlines tab).
    """
    from sqlalchemy import update

    now   = datetime.now(timezone.utc)
    where = and_(
        Notification.user_id  == attorney_id,
        Notification.is_read  == False,         # noqa: E712
    )
    if category:
        where = and_(where, Notification.category == category)

    await db.execute(
        update(Notification)
        .where(where)
        .values(is_read=True, read_at=now)
    )
    await db.commit()

    return {"message": "All notifications marked as read."}
