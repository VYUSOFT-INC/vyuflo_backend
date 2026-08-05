"""
app/schemas/admin/notifications_reminders.py

"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.attorney.notifications_reminders import (
    NotificationItemResponse as _AttyNotificationItem,
    NotificationListResponse,
    ReminderItemResponse,
    ReminderListResponse,
    TabCountsResponse,
)


class AdminNotificationItem(_AttyNotificationItem):
    """One item in the admin All Updates / Deadlines tab — spec §B2."""
    model_config = ConfigDict(from_attributes=True)

    triggered_by_user_id:   Optional[str] = None
    triggered_by_user_name: Optional[str] = None
    triggered_by_role:      Optional[str] = None   # native DB role name

    recipient_user_id:      str
    recipient_user_name:    Optional[str] = None
    recipient_role:         Optional[str] = None   # native DB role name


class AdminNotificationListResponse(BaseModel):
    """GET /admin/notifications-reminders/updates and /deadlines — spec §B2/§B4."""
    items:        List[AdminNotificationItem]
    total_unread: int
    has_more:     bool
    next_cursor:  Optional[str] = None