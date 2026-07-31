"""
notifications_reminders_router.py — V1 API routes for Notifications & Reminders (Screen 24).


Route map (5 endpoints):

  GET  /notifications-reminders/counts     → Tab badge counts (All 12, Deadlines 3)
  GET  /notifications-reminders/updates    → All Updates tab
  GET  /notifications-reminders/deadlines  → Deadlines tab
  GET  /notifications-reminders/reminders  → Reminders tab (calendar_events)
  POST /notifications-reminders/read-all   → Mark All as Read button

"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User
from app.services.attorney import notifications_reminders_service
from app.schemas.attorney.notifications_reminders import (
    NotificationListResponse,
    ReminderListResponse,
    TabCountsResponse,
)

notifications_reminders_router = APIRouter()


# ===========================================================================
# A. TAB COUNTS — badge numbers on the 3 tabs
# ===========================================================================

@notifications_reminders_router.get(
    "/notifications-reminders/counts",
    response_model=TabCountsResponse,
    summary="Tab badge counts — Screen 24",
)
async def get_tab_counts(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("notifications.view")),
) -> TabCountsResponse:
    """
    Screen 24 — called on page load and after any read/dismiss action.

    Returns:
    - all_updates_unread → "All Updates (12)" tab badge
    - reminders_total    → "Reminders" tab badge (upcoming reminders count)
    - deadlines_unread   → "Deadlines (3)" tab badge
    """
    return await notifications_reminders_service.get_tab_counts(
        db, current_user.user_id
    )


# ===========================================================================
# B. ALL UPDATES TAB
# ===========================================================================

@notifications_reminders_router.get(
    "/notifications-reminders/updates",
    response_model=NotificationListResponse,
    summary="All Updates tab — Screen 24",
)
async def list_updates(
    # Cursor-based pagination — "Load Older Notifications" button passes
    # the created_at of the last visible item as ?before=
    before: Optional[datetime] = Query(
        None,
        description="Cursor for Load Older button — pass created_at of last item seen",
    ),
    limit: int = Query(default=20, ge=1, le=50),

    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("notifications.view")),
) -> NotificationListResponse:
    """
    Screen 24 — All Updates tab.

    Returns all non-dismissed notifications newest first.
    Items are grouped by date (Today / Yesterday / older) on the frontend
    using each item's created_at field.

    Badge labels per notification_type:
    - task_assigned       → "Task Assigned"
    - deadline_approaching → "Urgent Deadline" (priority=urgent) or "Deadline"
    - document_approved   → "Document Added"
    - case_status_updated → "Case Update"

    Each item includes client_name, visa_type_code, case_reference
    derived from the linked application (shown as "John Doe - H-1B • #VF-2026-089").

    Pagination: omit `before` on first load → pass last item's created_at for next page.
    """
    return await notifications_reminders_service.list_updates(
        db, current_user.user_id, before=before, limit=limit
    )


# ===========================================================================
# C. DEADLINES TAB
# ===========================================================================

@notifications_reminders_router.get(
    "/notifications-reminders/deadlines",
    response_model=NotificationListResponse,
    summary="Deadlines tab — Screen 24",
)
async def list_deadlines(
    before: Optional[datetime] = Query(
        None,
        description="Cursor for Load Older button",
    ),
    limit: int = Query(default=20, ge=1, le=50),

    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("notifications.view")),
) -> NotificationListResponse:
    """
    Screen 24 — Deadlines tab.

    Returns only notifications with category='deadline', newest first.
    Subset of All Updates — same item shape, same cursor pagination.
    Badge shown as "Urgent Deadline" when priority=urgent.
    """
    return await notifications_reminders_service.list_deadlines(
        db, current_user.user_id, before=before, limit=limit
    )


# ===========================================================================
# D. REMINDERS TAB
# ===========================================================================

@notifications_reminders_router.get(
    "/notifications-reminders/reminders",
    response_model=ReminderListResponse,
    summary="Reminders tab — Screen 24",
)
async def list_reminders(
    include_past: bool = Query(
        default=False,
        description="False = upcoming reminders only (default). True = Load Older past reminders.",
    ),
    before: Optional[datetime] = Query(
        None,
        description="Cursor for Load Older past reminders — pass created_at of last item",
    ),
    limit: int = Query(default=20, ge=1, le=50),

    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("notifications.view")),
) -> ReminderListResponse:
    """
    Screen 24 — Reminders tab.

    Option A: queries calendar_events WHERE reminder_enabled=TRUE.
    No new table — uses existing CalendarEvent model.

    Default (include_past=False): upcoming reminders ordered soonest first.
    Load Older (include_past=True + before cursor): past reminders newest first.

    Badge label derived from reminder_minutes:
    - <= 60   → "1-Hour Reminder"
    - <= 1440 → "1-Day Reminder"   ← default (reminder_minutes=1440)
    - >  1440 → "2-Day Reminder"

    "+ New Reminder" button uses existing POST /calendar/events:
      { reminder_enabled: true, reminder_minutes: 1440, event_type: "consultation", ... }
    """
    return await notifications_reminders_service.list_reminders(
        db, current_user.user_id,
        before=before,
        limit=limit,
        include_past=include_past,
    )


# ===========================================================================
# E. MARK ALL AS READ — "Mark All as Read" button
# ===========================================================================

@notifications_reminders_router.post(
    "/notifications-reminders/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark All as Read — Screen 24 button",
)
async def mark_all_read(
    # Optional: scope to current tab
    # "deadline" → marks only Deadlines tab as read
    # omit → marks everything as read (All Updates button)
    category: Optional[str] = Query(
        None,
        description="Scope to tab: deadline | case_update | omit for all",
    ),

    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("notifications.view")),
) -> dict:
    """
    Screen 24 — "Mark All as Read" button (top right).

    Marks all unread notifications as read for the current attorney.
    Pass ?category=deadline to scope to Deadlines tab only.
    After this call, fetch /counts again to refresh all tab badges.
    """
    return await notifications_reminders_service.mark_all_read(
        db, current_user.user_id, category=category
    )
