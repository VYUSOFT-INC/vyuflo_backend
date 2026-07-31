# =============================================================================
# app/schemas/help.py
#
# NEW schemas for Lawyer Help & Support (Screens 28–36).
# Your existing app/schemas/admin/admin_support.py is NOT touched.
#
# Reuses from admin_support.py:
#   ArticleResponse, ArticleListResponse — imported directly in service
#   TicketCreate, TicketResponse         — imported directly in router
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Shared enums
# ─────────────────────────────────────────────────────────────────────────────

TicketStatus   = Literal["open", "in_progress", "waiting_user", "resolved", "closed"]
TicketPriority = Literal["urgent", "high", "medium", "low"]
TicketCategory = Literal[
    "account_profile", "active_cases", "documents",
    "billing_payments", "visa_types", "technical", "other",
]
NotificationCategory = Literal["case_update", "deadline", "news", "security", "billing"]
NotificationPriority = Literal["urgent", "high", "medium", "low"]


# =============================================================================
# TICKET SCHEMAS
# =============================================================================

class TicketCreate(BaseModel):
    """
    POST /help/tickets
    Lawyer submits a support ticket — optionally linked to an application.
    """
    subject:        str           = Field(..., min_length=5,  max_length=500)
    body:           str           = Field(..., min_length=10)
    category:       TicketCategory  = "technical"
    priority:       TicketPriority  = "medium"
    application_id: Optional[uuid.UUID] = None   # Screen 32 application picker


class TicketSummaryResponse(BaseModel):
    """
    One row in Screen 33 — My Tickets list.
    Lightweight — no replies included.
    """
    id:            uuid.UUID
    ticket_number: str
    subject:       str
    category:      TicketCategory
    priority:      TicketPriority
    status:        TicketStatus
    reply_count:   int = 0          # computed in service
    created_at:    datetime
    updated_at:    datetime

    model_config = ConfigDict(from_attributes=True)


class TicketListResponse(BaseModel):
    """Screen 33 — My Tickets list + status counts for tab badges."""
    items:      List[TicketSummaryResponse]
    total:      int
    open:       int   # count of open tickets
    in_progress: int
    resolved:   int


# ─────────────────────────────────────────────────────────────────────────────
# Ticket Reply schemas
# ─────────────────────────────────────────────────────────────────────────────

class TicketReplyCreate(BaseModel):
    """POST /help/tickets/{id}/replies"""
    body: str = Field(..., min_length=1, max_length=10000)


class TicketReplyResponse(BaseModel):
    """One message bubble in Screen 34 reply thread."""
    id:               uuid.UUID
    ticket_id:        uuid.UUID
    sender_id:        Optional[uuid.UUID]
    sender_type:      str          # "user" | "agent" | "system"
    body:             str
    is_read:          bool
    is_internal_note: bool
    created_at:       datetime

    model_config = ConfigDict(from_attributes=True)


class TicketDetailResponse(BaseModel):
    """
    Screen 34 — Ticket Detail + replies thread.
    Screen 35 — Ticket Submitted confirmation (same shape, replies=[]).
    """
    id:             uuid.UUID
    ticket_number:  str
    subject:        str
    body:           str
    category:       TicketCategory
    priority:       TicketPriority
    status:         TicketStatus
    application_id: Optional[uuid.UUID]
    created_at:     datetime
    updated_at:     datetime
    replies:        List[TicketReplyResponse] = []

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# NOTIFICATION SCHEMAS  (Screen 36)
# =============================================================================

class NotificationResponse(BaseModel):
    """One row in Screen 36 — past notifications list."""
    id:                uuid.UUID
    notification_type: str
    category:          NotificationCategory
    priority:          NotificationPriority
    title:             str
    body:              str
    application_id:    Optional[uuid.UUID]
    case_reference:    Optional[str]
    cta_primary_label: Optional[str]
    cta_primary_url:   Optional[str]
    is_read:           bool
    read_at:           Optional[datetime]
    is_dismissed:      bool
    sent_via_email:    bool
    sent_via_push:     bool
    sent_via_sms:      bool
    created_at:        datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Screen 36 — paginated notification history."""
    items:       List[NotificationResponse]
    total:       int
    unread_count: int    # for badge on bell icon
