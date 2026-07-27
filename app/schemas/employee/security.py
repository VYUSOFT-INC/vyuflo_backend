from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LoginSessionResponse(BaseModel):
    """One row of the Login History list (screenshot 3)."""
    id: uuid.UUID
    browser: Optional[str] = None
    os: Optional[str] = None
    device_type: str
    city: Optional[str] = None
    country: Optional[str] = None
    is_current_session: bool
    created_at: datetime
    logged_out_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LoginHistoryListResponse(BaseModel):
    items: list[LoginSessionResponse]
    total: int


class SecurityAlertPreferencesResponse(BaseModel):
    """
    The 8 Email/SMS checkboxes in the Security Alerts screen (screenshot 2).
    Field names match the notify_* columns on NotificationPreferences exactly —
    model_validate() maps by name, so these must stay in sync with the model.
    """
    notify_new_device_login_email: bool
    notify_new_device_login_sms: bool
    notify_failed_login_email: bool
    notify_failed_login_sms: bool
    notify_password_changed_email: bool
    notify_password_changed_sms: bool
    notify_unusual_activity_email: bool
    notify_unusual_activity_sms: bool

    model_config = {"from_attributes": True}


class SecurityAlertPreferencesUpdate(BaseModel):
    """
    PATCH body — every field optional, so the client only has to send
    the checkbox(es) that actually changed.
    """
    notify_new_device_login_email: Optional[bool] = None
    notify_new_device_login_sms: Optional[bool] = None
    notify_failed_login_email: Optional[bool] = None
    notify_failed_login_sms: Optional[bool] = None
    notify_password_changed_email: Optional[bool] = None
    notify_password_changed_sms: Optional[bool] = None
    notify_unusual_activity_email: Optional[bool] = None
    notify_unusual_activity_sms: Optional[bool] = None
