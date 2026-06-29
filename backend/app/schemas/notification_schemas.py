# =============================================================================
# app/schemas/notification_schemas.py
# Pydantic v2 schemas for Notifications (TABLE 25) + Preferences (TABLE 26)
# =============================================================================
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Notification (TABLE 25)
# =============================================================================

class NotificationOut(ORMBase):
    id:                uuid.UUID
    user_id:           uuid.UUID
    notification_type: str
    category:          str
    priority:          str
    title:             str
    body:              str
    application_id:    Optional[uuid.UUID] = None
    document_id:       Optional[uuid.UUID] = None
    case_reference:    Optional[str]       = None
    actor_id:          Optional[uuid.UUID] = None
    actor_label:       Optional[str]       = None
    cta_primary_label:    Optional[str] = None
    cta_primary_url:      Optional[str] = None
    cta_secondary_label:  Optional[str] = None
    cta_secondary_url:    Optional[str] = None
    is_read:      bool
    read_at:      Optional[datetime] = None
    is_dismissed: bool
    dismissed_at: Optional[datetime] = None
    sent_via_email: bool
    sent_via_push:  bool
    sent_via_sms:   bool
    expires_at:     Optional[datetime] = None
    created_at:     datetime
    updated_at:     datetime


class NotificationListResponse(BaseModel):
    items:        List[NotificationOut]
    total:        int
    unread_count: int
    urgent_count: int
    has_more:     bool


class NotificationStatsResponse(BaseModel):
    urgent_count: int
    unread_count: int
    week_count:   int
    news_count:   int


class MarkReadResponse(BaseModel):
    updated: int
    message: str


class MarkAllReadRequest(BaseModel):
    category: Optional[str] = None   # filter to one category only


# =============================================================================
# Notification Preferences (TABLE 26)
# =============================================================================

class NotificationPreferencesOut(ORMBase):
    id:      uuid.UUID
    user_id: uuid.UUID
    email_enabled: bool
    push_enabled:  bool
    sms_enabled:   bool
    notify_case_updates:     bool
    notify_deadlines:        bool
    notify_document_updates: bool
    notify_news:             bool
    notify_security_alerts:  bool
    notify_billing:          bool
    notify_weekly_summary:   bool
    updated_at: datetime


class UpdatePreferencesRequest(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled:  Optional[bool] = None
    sms_enabled:   Optional[bool] = None
    notify_case_updates:     Optional[bool] = None
    notify_deadlines:        Optional[bool] = None
    notify_document_updates: Optional[bool] = None
    notify_news:             Optional[bool] = None
    notify_security_alerts:  Optional[bool] = None
    notify_billing:          Optional[bool] = None
    notify_weekly_summary:   Optional[bool] = None