# =============================================================================
# app/schemas/screen12_schemas.py
# Screen 12 — Secure Messages
#
# Covers:
#   - MessageTemplateResponse / Create / Update / ListResponse
#   - ThreadResponse enhancements (action_required, thread_status,
#     case_number, visa_type_code)
#
# NOTE on ThreadResponse:
#   Add the 4 new fields below directly into your existing ThreadResponse
#   in app/schemas/message.py — do NOT create a second ThreadResponse.
#   They are shown here as a clear reference for what to add.
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# =============================================================================
# MESSAGE TEMPLATES
# Powers the reply-chip bar at the bottom of the compose box on Screen 12:
#   "Please re-upload cleaner scan" | "Document approved" | "Missing signature…"
# =============================================================================

class MessageTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         uuid.UUID
    name:       str            # chip label shown in the bar
    body:       str            # text injected into compose box on click
    category:   Optional[str] = None   # "document" | "approval" | "general" | "follow_up"
    sort_order: int
    is_active:  bool
    created_at: datetime


class MessageTemplateListResponse(BaseModel):
    items: list[MessageTemplateResponse]
    total: int


class MessageTemplateCreate(BaseModel):
    """POST /messages/templates — admin only."""
    name:       str
    body:       str
    category:   Optional[str] = None
    sort_order: int  = 0
    is_active:  bool = True


class MessageTemplateUpdate(BaseModel):
    """PATCH /messages/templates/{id} — admin only, all fields optional."""
    name:       Optional[str]  = None
    body:       Optional[str]  = None
    category:   Optional[str]  = None
    sort_order: Optional[int]  = None
    is_active:  Optional[bool] = None


# =============================================================================
# THREAD RESPONSE ADDITIONS
#
# Add these 4 fields to the existing ThreadResponse in app/schemas/message.py:
#
#     action_required: bool         = False
#     thread_status:   str          = "active"   # "active" | "pending" | "resolved"
#     case_number:     Optional[str] = None       # Application.application_number
#     visa_type_code:  Optional[str] = None       # VisaType.code e.g. "H-1B"
#
# This class is for reference only — do not use it separately.
# =============================================================================

class ThreadResponseAdditions(BaseModel):
    """
    Reference only — copy these fields into your existing ThreadResponse.
    Do not register this as a separate schema.
    """
    action_required: bool          = False
    thread_status:   str           = "active"
    case_number:     Optional[str] = None
    visa_type_code:  Optional[str] = None
