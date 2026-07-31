"""
app/schemas/notification_template.py  ← FINAL CORRECT VERSION
Replace your existing app/schemas/notification_template.py with this.

Matches the Notification Templates screen exactly:
  - Template Name + description shown in list
  - Channel badge (Email / In-App / SMS / Push)
  - Trigger Event (event_key shown as "Status_Changed_Approved" etc.)
  - Last Modified + "by [user name]"
  - Status toggle (is_active)
  - Search + filter by channel / trigger / status
  - Pagination
"""
from __future__ import annotations

import json
import uuid
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.security import datetime

VALID_CHANNELS   = {"email", "sms", "in_app", "push"}
VALID_CATEGORIES = {"case_update", "deadline", "news", "security", "billing"}


# =============================================================================
# Base
# =============================================================================
class NotificationTemplateBase(BaseModel):
    event_key:              str           = Field(..., max_length=100,
                                                  description="Stable trigger key: 'case_status_updated'. "
                                                              "Shown on screen as 'Status_Changed_Approved'. "
                                                              "NEVER change after creation.")
    name:                   str           = Field(..., max_length=255,
                                                  description="Display name: 'Visa Application Approved'")
    description:            Optional[str] = Field(None,
                                                  description="Sub-title shown in list: "
                                                              "'Sent to applicant upon final approval'")
    channel:                str           = Field(..., description="email | sms | in_app | push")
    subject:                Optional[str] = Field(None, max_length=500,
                                                  description="Email subject line. Required when channel=email.")
    body_html:              Optional[str] = Field(None, description="HTML body. Email only.")
    body_text:              str           = Field(..., description="Plain text body with {{placeholders}}")
    available_placeholders: Optional[str] = Field(None,
                                                  description='JSON array as string: '
                                                              '["{{user_name}}", "{{application_number}}"]')
    category:               str           = Field(...)
    is_active:              bool          = True

    @field_validator("channel")
    @classmethod
    def check_channel(cls, v: str) -> str:
        if v not in VALID_CHANNELS:
            raise ValueError(f"channel must be one of {VALID_CHANNELS}")
        return v

    @field_validator("category")
    @classmethod
    def check_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        return v

    @field_validator("available_placeholders")
    @classmethod
    def check_placeholders_json(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                parsed = json.loads(v)
                if not isinstance(parsed, list):
                    raise ValueError("must be a JSON array")
            except json.JSONDecodeError:
                raise ValueError("available_placeholders must be valid JSON string")
        return v

    @field_validator("subject")
    @classmethod
    def subject_required_for_email(cls, v: Optional[str], info: Any) -> Optional[str]:
        if info.data.get("channel") == "email" and not v:
            raise ValueError("subject is required when channel is 'email'")
        return v


# =============================================================================
# CREATE  (POST /notification-templates)
# =============================================================================
class NotificationTemplateCreate(NotificationTemplateBase):
    pass


# =============================================================================
# UPDATE  (PATCH /notification-templates/{id})
# event_key and channel are intentionally immutable after creation.
# =============================================================================
class NotificationTemplateUpdate(BaseModel):
    name:                   Optional[str]  = Field(None, max_length=255)
    description:            Optional[str]  = None
    subject:                Optional[str]  = Field(None, max_length=500)
    body_html:              Optional[str]  = None
    body_text:              Optional[str]  = None
    available_placeholders: Optional[str]  = None
    is_active:              Optional[bool] = None


# =============================================================================
# TOGGLE  (PATCH /notification-templates/{id}/toggle)
# The on/off switch shown in the Status column of the list
# =============================================================================
class NotificationTemplateToggle(BaseModel):
    is_active: bool


# =============================================================================
# RESPONSE — includes last_modified_by_name for "by Sarah J." shown in list
# =============================================================================
class NotificationTemplateResponse(BaseModel):
    id:                     uuid.UUID
    event_key:              str
    name:                   str
    description:            Optional[str]
    channel:                str
    subject:                Optional[str]
    body_html:              Optional[str]
    body_text:              str
    available_placeholders: Optional[str]
    category:               str
    is_active:              bool
    # These two power the "Last Modified — Oct 24, 2023 — by Sarah J." column
    updated_at:             datetime
    last_modified_by_name:  Optional[str] = None
    created_at:             datetime

    model_config = {"from_attributes": True,
                    "arbitrary_types_allowed": True,
                    }

    # def model_post_init(self, __context: Any) -> None:
    #     for f in ("created_at", "updated_at"):
    #         v = getattr(self, f, None)
    #         if v is not None and not isinstance(v, str):
    #             object.__setattr__(self, f, str(v))


# =============================================================================
# LIST RESPONSE — matches "Showing 1 to 10 of 24 results" + pagination
# =============================================================================
class NotificationTemplateListResponse(BaseModel):
    items:       List[NotificationTemplateResponse]
    total:       int
    page:        int = 1
    limit:       int = 10
    total_pages: int = 1