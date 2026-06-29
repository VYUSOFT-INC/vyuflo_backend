# =============================================================================
# app/services/notification_service.py
# Business logic for Notifications (TABLE 25) + Preferences (TABLE 26)
# =============================================================================
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import Notification, NotificationPreferences
from app.schemas.notification_schemas import (
    NotificationListResponse,
    NotificationOut,
    NotificationStatsResponse,
    MarkReadResponse,
    UpdatePreferencesRequest,
    NotificationPreferencesOut,
)

PAGE_SIZE_DEFAULT = 20


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# LIST
# =============================================================================

async def list_notifications(
    db:       AsyncSession,
    user_id:  uuid.UUID,
    *,
    category: Optional[str] = None,
    is_read:  Optional[bool] = None,
    priority: Optional[str] = None,
    limit:    int = PAGE_SIZE_DEFAULT,
    offset:   int = 0,
) -> NotificationListResponse:

    filters = [
        Notification.user_id     == user_id,
        Notification.is_dismissed == False,  # noqa: E712
    ]
    if category: filters.append(Notification.category == category)
    if is_read  is not None: filters.append(Notification.is_read == is_read)
    if priority: filters.append(Notification.priority == priority)

    # Total matching
    count_q = select(func.count()).select_from(Notification).where(and_(*filters))
    total   = (await db.scalar(count_q)) or 0

    # Unread count (always for the user, regardless of filter)
    unread_q = select(func.count()).select_from(Notification).where(
        and_(Notification.user_id == user_id,
             Notification.is_read == False,      # noqa: E712
             Notification.is_dismissed == False) # noqa: E712
    )
    unread_count = (await db.scalar(unread_q)) or 0

    # Urgent count
    urgent_q = select(func.count()).select_from(Notification).where(
        and_(Notification.user_id  == user_id,
             Notification.priority == "urgent",
             Notification.is_dismissed == False) # noqa: E712
    )
    urgent_count = (await db.scalar(urgent_q)) or 0

    # Paginated rows — newest first
    rows_q = (
        select(Notification)
        .where(and_(*filters))
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(rows_q)
    items  = list(result.scalars().all())

    return NotificationListResponse(
        items        = [NotificationOut.model_validate(n) for n in items],
        total        = total,
        unread_count = unread_count,
        urgent_count = urgent_count,
        has_more     = (offset + limit) < total,
    )


# =============================================================================
# STATS (for the 4 stat cards)
# =============================================================================

async def get_notification_stats(
    db:      AsyncSession,
    user_id: uuid.UUID,
) -> NotificationStatsResponse:

    base = and_(
        Notification.user_id     == user_id,
        Notification.is_dismissed == False,  # noqa: E712
    )
    week_ago = _now() - timedelta(days=7)

    urgent_count = (await db.scalar(
        select(func.count()).select_from(Notification)
        .where(and_(base, Notification.priority == "urgent"))
    )) or 0

    unread_count = (await db.scalar(
        select(func.count()).select_from(Notification)
        .where(and_(base, Notification.is_read == False))  # noqa: E712
    )) or 0

    week_count = (await db.scalar(
        select(func.count()).select_from(Notification)
        .where(and_(base, Notification.created_at >= week_ago))
    )) or 0

    news_count = (await db.scalar(
        select(func.count()).select_from(Notification)
        .where(and_(base, Notification.category == "news"))
    )) or 0

    return NotificationStatsResponse(
        urgent_count = urgent_count,
        unread_count = unread_count,
        week_count   = week_count,
        news_count   = news_count,
    )


# =============================================================================
# MARK READ / DISMISS
# =============================================================================

async def mark_notification_read(
    db:      AsyncSession,
    user_id: uuid.UUID,
    notif_id: uuid.UUID,
) -> MarkReadResponse:
    result = await db.execute(
        update(Notification)
        .where(and_(
            Notification.id      == notif_id,
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        ))
        .values(is_read=True, read_at=_now())
        .returning(Notification.id)
    )
    updated = len(result.all())
    await db.flush()
    return MarkReadResponse(updated=updated, message="Marked as read.")


async def mark_all_read(
    db:       AsyncSession,
    user_id:  uuid.UUID,
    category: Optional[str] = None,
) -> MarkReadResponse:
    filters = [
        Notification.user_id == user_id,
        Notification.is_read == False,  # noqa: E712
    ]
    if category:
        filters.append(Notification.category == category)

    result = await db.execute(
        update(Notification)
        .where(and_(*filters))
        .values(is_read=True, read_at=_now())
        .returning(Notification.id)
    )
    updated = len(result.all())
    await db.flush()
    return MarkReadResponse(updated=updated, message=f"Marked {updated} notifications as read.")


async def dismiss_notification(
    db:       AsyncSession,
    user_id:  uuid.UUID,
    notif_id: uuid.UUID,
) -> MarkReadResponse:
    result = await db.execute(
        update(Notification)
        .where(and_(
            Notification.id      == notif_id,
            Notification.user_id == user_id,
        ))
        .values(is_dismissed=True, dismissed_at=_now(), is_read=True, read_at=_now())
        .returning(Notification.id)
    )
    updated = len(result.all())
    await db.flush()
    return MarkReadResponse(updated=updated, message="Dismissed.")


# =============================================================================
# PREFERENCES
# =============================================================================

async def get_preferences(
    db:      AsyncSession,
    user_id: uuid.UUID,
) -> NotificationPreferencesOut:
    prefs = await db.scalar(
        select(NotificationPreferences)
        .where(NotificationPreferences.user_id == user_id)
    )
    if not prefs:
        # Auto-create with defaults if first time
        prefs = NotificationPreferences(
            id          = uuid.uuid4(),
            user_id     = user_id,
            created_by  = user_id,
            modified_by = user_id,
        )
        db.add(prefs)
        await db.flush()
        await db.refresh(prefs)
    return NotificationPreferencesOut.model_validate(prefs)


async def update_preferences(
    db:      AsyncSession,
    user_id: uuid.UUID,
    data:    UpdatePreferencesRequest,
) -> NotificationPreferencesOut:
    prefs = await db.scalar(
        select(NotificationPreferences)
        .where(NotificationPreferences.user_id == user_id)
    )
    if not prefs:
        prefs = NotificationPreferences(
            id      = uuid.uuid4(),
            user_id = user_id,
            created_by  = user_id,
            modified_by = user_id,
        )
        db.add(prefs)

    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    payload["modified_by"] = user_id
    for k, v in payload.items():
        if hasattr(prefs, k):
            setattr(prefs, k, v)

    await db.flush()
    await db.refresh(prefs)
    return NotificationPreferencesOut.model_validate(prefs)