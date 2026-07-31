"""
notifications_reminders_schema.py — Pydantic schemas for Notifications & Reminders (Screen 24).

FILE LOCATION
    app/schemas/attorney/notifications_reminders.py

Covers all sections of Screen 24:
  All Updates tab   •  Reminders tab  •  Deadlines tab
  Notification item •  Reminder item  •  Mark All as Read
  Load Older (cursor pagination)      •  + New Reminder button

Existing schemas in app/schemas/notification_schemas.py are NOT redefined:
  NotificationPreferencesOut    → reused for Screen 13 settings
  UpdatePreferencesRequest      → reused for Screen 13 settings
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# NOTIFICATION ITEM — All Updates + Deadlines tabs
# ===========================================================================

class NotificationItemResponse(BaseModel):
    """
    One item in the All Updates or Deadlines tab list.

    badge_label is derived from notification_type:
      task_assigned       → "Task Assigned"
      deadline_approaching → "Urgent Deadline" (if priority=urgent) or "Deadline"
      document_approved   → "Document Added"
      case_status_updated → "Case Update"
    """
    model_config = ConfigDict(from_attributes=True)

    id:                uuid.UUID
    notification_type: str        # raw enum value
    badge_label:       str        # derived display label shown on card
    category:          str        # case_update | deadline | news | security | billing
    priority:          str        # urgent | high | medium | low

    title:  str
    body:   str

    # Case reference shown as "John Doe - H-1B  •  #VF-2026-089"
    client_name:       Optional[str] = None   # from application.user.first_name + last_name
    visa_type_code:    Optional[str] = None   # "H-1B", "O-1A" etc.
    case_reference:    Optional[str] = None   # application_number e.g. "#VF-2026-089"

    # Timing display e.g. "Due in 4 hours", "Yesterday, 4:30 PM"
    created_at: datetime

    is_read:      bool
    is_dismissed: bool

    # Unread dot shown top-right of card
    show_unread_dot: bool   # = not is_read


class NotificationListResponse(BaseModel):
    """
    Response for GET /notifications-reminders/updates
    and GET /notifications-reminders/deadlines.

    Cursor-based pagination powers "Load Older Notifications" button.
    """
    items:          List[NotificationItemResponse]
    total_unread:   int
    has_more:       bool
    next_cursor:    Optional[datetime] = None   # created_at of last item → pass as ?before=


# ===========================================================================
# REMINDER ITEM — Reminders tab
# ===========================================================================

class ReminderItemResponse(BaseModel):
    """
    One item in the Reminders tab.
    Sourced from calendar_events WHERE reminder_enabled=TRUE.

    badge_label derived from reminder_minutes:
      reminder_minutes <= 60   → "1-Hour Reminder"
      reminder_minutes <= 1440 → "1-Day Reminder"
      reminder_minutes >  1440 → "2-Day Reminder"

    Scheduled time shown as "Tomorrow, 10:00 AM" or "Today, 3:00 PM".
    """
    model_config = ConfigDict(from_attributes=True)

    id:          uuid.UUID     # calendar_event.id
    title:       str
    badge_label: str           # "1-Day Reminder", "1-Hour Reminder" etc.

    event_date:  date
    start_time:  Optional[time] = None
    # Displayed as: "Tomorrow, 10:00 AM"

    reminder_minutes: int      # 15 | 30 | 60 | 1440 | 2880

    # Case reference shown as "Sarah Smith - L-1A  •  #VF-2026-092"
    client_name:    Optional[str] = None
    visa_type_code: Optional[str] = None
    case_reference: Optional[str] = None   # application_number

    is_upcoming: bool   # event_date >= today → unread dot shown
    created_at:  datetime


class ReminderListResponse(BaseModel):
    """Response for GET /notifications-reminders/reminders."""
    items:    List[ReminderItemResponse]
    total:    int
    has_more: bool
    next_cursor: Optional[datetime] = None


# ===========================================================================
# TAB COUNTS — drives the badge numbers on tabs
# ===========================================================================

class TabCountsResponse(BaseModel):
    """
    GET /notifications-reminders/counts
    Powers the badge numbers on the 3 tabs:
      All Updates (12) | Reminders | Deadlines (3)
    """
    all_updates_unread: int   # unread count across all notification categories
    reminders_total:    int   # upcoming reminders (event_date >= today)
    deadlines_unread:   int   # unread notifications with category="deadline"
