"""
app/routes/admin/notifications_reminders.py

Section B spec — admin cross-role notification feed.
Mounted in main.py as:
    app.include_router(admin_notifications_router, prefix="/api/v1")
Resolves to /api/v1/admin/notifications-reminders/*

role_filter accepts NATIVE role names: hr | app_admin | employee | attorney | all
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, status

from app.core.dependencies import Current_User, DBSession
from app.core.core_permissions import PermissionChecker
from app.schemas.admin.notifications_reminders import AdminNotificationListResponse
from app.schemas.attorney.notifications_reminders import ReminderListResponse, TabCountsResponse
from app.services.admin import admin_notifications_service

admin_notifications_router = APIRouter(
    prefix="/admin/notifications-reminders",
    tags=["Admin — Notifications"],
)

_require_view = PermissionChecker("notifications.view_all")


@admin_notifications_router.get(
    "/counts",
    response_model=TabCountsResponse,
    summary="Admin tab badge counts — cross-role",
)
async def counts(
    db: DBSession,
    _: Current_User = _require_view,
    role_filter: str = Query("all"),
    user_id: Optional[uuid.UUID] = Query(None),
) -> TabCountsResponse:
    return await admin_notifications_service.get_tab_counts(
        db, role_filter=role_filter, user_id=user_id,
    )


@admin_notifications_router.get(
    "/updates",
    response_model=AdminNotificationListResponse,
    summary="All Updates tab — cross-role",
)
async def updates(
    db: DBSession,
    _: Current_User = _require_view,
    role_filter: str = Query("all"),
    user_id: Optional[uuid.UUID] = Query(None),
    before: Optional[datetime] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> AdminNotificationListResponse:
    return await admin_notifications_service.list_updates(
        db, role_filter=role_filter, user_id=user_id, before=before, limit=limit,
    )


@admin_notifications_router.get(
    "/deadlines",
    response_model=AdminNotificationListResponse,
    summary="Deadlines tab — cross-role",
)
async def deadlines(
    db: DBSession,
    _: Current_User = _require_view,
    role_filter: str = Query("all"),
    user_id: Optional[uuid.UUID] = Query(None),
    before: Optional[datetime] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> AdminNotificationListResponse:
    return await admin_notifications_service.list_deadlines(
        db, role_filter=role_filter, user_id=user_id, before=before, limit=limit,
    )


@admin_notifications_router.get(
    "/reminders",
    response_model=ReminderListResponse,
    summary="Reminders tab — cross-role (all attorneys' calendar reminders)",
)
async def reminders(
    db: DBSession,
    _: Current_User = _require_view,
    include_past: bool = Query(False),
    user_id: Optional[uuid.UUID] = Query(None),
    before: Optional[datetime] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> ReminderListResponse:
    return await admin_notifications_service.list_reminders(
        db, user_id=user_id, before=before, limit=limit, include_past=include_past,
    )


@admin_notifications_router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Mark all as read — cross-role, optionally scoped",
)
@admin_notifications_router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Mark all as read — cross-role, optionally scoped",
)
@admin_notifications_router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Mark all as read — cross-role, optionally scoped",
)
@admin_notifications_router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Mark all as read — cross-role, optionally scoped",
)
@admin_notifications_router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Mark all as read — cross-role, optionally scoped",
)
async def read_all(
    db: DBSession,
    current_user: Current_User,
    _: Current_User = _require_view,
    category: Optional[str] = Query(None),
    role_filter: str = Query("all"),
    user_id: Optional[uuid.UUID] = Query(None),
) -> None:
    await admin_notifications_service.mark_all_read(
        db, category=category, role_filter=role_filter, user_id=user_id,
    )
