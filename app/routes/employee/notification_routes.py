# =============================================================================
# app/api/v1/notification_routes.py
#
# Register in main.py:
#   from app.api.v1.notification_routes import router as notification_router
#   app.include_router(notification_router, prefix="/api/v1", tags=["notifications"])
# =============================================================================
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User
from app.schemas.employee.notification_schemas import (
    NotificationOut,
    NotificationListResponse,
    NotificationStatsResponse,
    MarkReadResponse,
    MarkAllReadRequest,
    NotificationPreferencesOut,
    UpdatePreferencesRequest,
)
from app.services.employee.notification_service import (
    list_notifications,
    get_notification_stats,
    mark_notification_read,
    mark_all_read,
    dismiss_notification,
    get_preferences,
    update_preferences,
)

notification_router = APIRouter()


# =============================================================================
# LIST
# =============================================================================

@notification_router.get(
    "/notifications",
    response_model=NotificationListResponse,
    summary="List notifications for the current user",
    description="""
    Returns paginated notifications, newest first.
    Dismissed notifications are always excluded.

    **Query params (all optional):**
    - `category` — filter by `case_update | deadline | news | security | billing`
    - `is_read`  — `true` = read only, `false` = unread only, omit = all
    - `priority` — filter by `urgent | high | medium | low`
    - `limit`    — page size (default 20, max 100)
    - `offset`   — pagination offset

    **Response includes:**
    - `unread_count` / `urgent_count` — always for the whole user, ignoring filters
    - `has_more` — true if more pages exist
    """,
)
async def api_list_notifications(
    category: Optional[str] = Query(None),
    is_read:  Optional[bool] = Query(None),
    priority: Optional[str] = Query(None),
    limit:    int            = Query(20, ge=1, le=100),
    offset:   int            = Query(0,  ge=0),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
) -> NotificationListResponse:
    return await list_notifications(
        db, current_user.user_id,
        category=category,
        is_read=is_read,
        priority=priority,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# STATS
# =============================================================================

@notification_router.get(
    "/notifications/stats",
    response_model=NotificationStatsResponse,
    summary="Notification stats — drives the 4 stat cards on the page",
)
async def api_notification_stats(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
) -> NotificationStatsResponse:
    return await get_notification_stats(db, current_user.user_id)


# =============================================================================
# PREFERENCES  (must come BEFORE /{notif_id} to avoid route collision)
# =============================================================================

@notification_router.get(
    "/notifications/preferences",
    response_model=NotificationPreferencesOut,
    summary="Get notification preferences — auto-creates defaults on first call",
)
async def api_get_preferences(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
) -> NotificationPreferencesOut:
    return await get_preferences(db, current_user.user_id)


@notification_router.patch(
    "/notifications/preferences",
    response_model=NotificationPreferencesOut,
    summary="Update notification preferences — send only fields you want to change",
)
async def api_update_preferences(
    body:         UpdatePreferencesRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
) -> NotificationPreferencesOut:
    print(current_user)
    updated = await update_preferences(db, current_user.user_id, body)
    await db.commit()
    return updated


# =============================================================================
# MARK ALL READ
# =============================================================================

@notification_router.post(
    "/notifications/read-all",
    response_model=MarkReadResponse,
    summary="Mark all (or all in a category) as read",
)
async def api_mark_all_read(
    body:         MarkAllReadRequest = MarkAllReadRequest(),
    db:           AsyncSession       = Depends(get_db),
    current_user: User               = Depends(get_current_user),
) -> MarkReadResponse:
    result = await mark_all_read(db, current_user.user_id, body.category)
    await db.commit()
    return result


# =============================================================================
# SINGLE NOTIFICATION — get / mark-read / dismiss
# =============================================================================

@notification_router.get(
    "/notifications/{notif_id}",
    response_model=NotificationOut,
    summary="Get a single notification by ID",
)
async def api_get_notification(
    notif_id:     uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
) -> NotificationOut:
    from sqlalchemy import select
    from app.models.visamodels import Notification
    result = await db.execute(
        select(Notification).where(
            Notification.id      == notif_id,
            Notification.user_id == current_user.user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Notification not found.")
    return NotificationOut.model_validate(notif)


@notification_router.post(
    "/notifications/{notif_id}/read",
    response_model=MarkReadResponse,
    summary="Mark a single notification as read",
)
async def api_mark_read(
    notif_id:     uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
) -> MarkReadResponse:
    result = await mark_notification_read(db, current_user.user_id, notif_id)
    await db.commit()
    return result


@notification_router.post(
    "/notifications/{notif_id}/dismiss",
    response_model=MarkReadResponse,
    summary="Dismiss a notification (hides it permanently from the list)",
)
async def api_dismiss(
    notif_id:     uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
) -> MarkReadResponse:
    result = await dismiss_notification(db, current_user.user_id, notif_id)
    await db.commit()
    return result