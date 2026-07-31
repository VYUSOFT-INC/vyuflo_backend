"""
app/schemas/admin_support_schema.py

Pydantic v2 schemas for ADMIN-12 Help & Support (Admin).

Screen sections covered:
  - Search articles / FAQs
  - Category tab filter
  - FAQ accordion list
  - Popular Articles sidebar
  - System Status card  (reads from system_settings table — no new table)
  - Submit a Ticket (Create Ticket button)

No new DB tables required. All data comes from:
  - support_articles  → FAQs, Popular Articles
  - system_settings   → System Status card
  - support_tickets   → Submit a Ticket
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# ARTICLE / FAQ  SCHEMAS
# =============================================================================

class ArticleResponse(BaseModel):
    """Single article / FAQ item returned to the frontend."""
    model_config = ConfigDict(from_attributes=True)

    id:           uuid.UUID
    title:        str
    summary:      Optional[str] = None
    body:         Optional[str] = None   # Only returned on detail endpoint
    article_type: str                    # "faq" | "guide" | "video_tutorial" | "policy"
    category:     str                    # "all" | "platform_config" | "user_management" | ...
    tag:          Optional[str] = None
    view_count:   int = 0
    is_featured:  bool = False
    published_at: Optional[datetime] = None
    updated_at:   datetime


class ArticleListResponse(BaseModel):
    """Paginated list of articles — used by search + FAQ list + Popular Articles."""
    items:       List[ArticleResponse]
    total:       int
    page:        int
    limit:       int
    total_pages: int


# =============================================================================
# SYSTEM STATUS  SCHEMAS
# (Data stored in system_settings table — no new table needed)
# =============================================================================

class ServiceStatusItem(BaseModel):
    """One row in the System Status card."""
    service_name:  str           # e.g. "Core Platform"
    status:        str           # "operational" | "degraded" | "down"
    uptime_label:  Optional[str] = None  # e.g. "100% Uptime", "99.9% Uptime"
    status_badge:  str           # "All Systems Operational" | "Partial Outage" | "Outage"


class SystemStatusResponse(BaseModel):
    """Full System Status card response."""
    overall_status: str                    # "All Systems Operational" | "Partial Outage" | "Outage"
    services:       List[ServiceStatusItem]
    view_status_page_url: Optional[str] = None


# =============================================================================
# TICKET  SCHEMAS  (Submit a Ticket — "Create Ticket" button)
# =============================================================================

class TicketCreate(BaseModel):
    """Payload for POST /admin/support/tickets"""
    subject:  str  = Field(..., min_length=5,  max_length=500)
    body:     str  = Field(..., min_length=10)
    category: str  = Field(default="technical")
    # Allowed: "account_profile" | "active_cases" | "documents"
    #          "billing_payments" | "visa_types" | "technical" | "other"
    priority: str  = Field(default="medium")
    # Allowed: "urgent" | "high" | "medium" | "low"


class TicketResponse(BaseModel):
    """Response after creating a support ticket."""
    model_config = ConfigDict(from_attributes=True)

    id:            uuid.UUID
    ticket_number: str
    subject:       str
    category:      str
    priority:      str
    status:        str
    created_at:    datetime
