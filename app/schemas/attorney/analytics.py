"""
analytics_schema.py — Pydantic schemas for Lawyer Analytics Dashboard (Screen 23).

FILE LOCATION
    app/schemas/attorney/analytics.py

Covers all widgets:
  KPI Cards  •  Case Status Chart  •  Cases by Visa Type
  Caseload Over Time  •  Case Success Rate  •  Upcoming Actions Table
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# KPI CARDS  —  GET /analytics/kpi-cards
# ===========================================================================

class KpiCardsResponse(BaseModel):
    """Powers the 5 stat cards at the top of the dashboard."""
    active_cases:             int
    new_clients_month:        int
    avg_case_duration_days:   float
    pending_actions:          int
    monthly_revenue:          Optional[float] = Field(
        None,
        description="Null until billing module is live.",
    )


# ===========================================================================
# CASE STATUS BREAKDOWN  —  GET /analytics/case-status
# ===========================================================================

class CaseStatusItem(BaseModel):
    status:     str    = Field(..., examples=["in_progress"])
    label:      str    = Field(..., examples=["In Progress"])
    count:      int
    percentage: float  = Field(..., description="0–100")
    color_hex:  str    = Field(..., examples=["#3B82F6"])


class CaseStatusResponse(BaseModel):
    items: List[CaseStatusItem]
    total: int


# ===========================================================================
# CASES BY VISA TYPE  —  GET /analytics/cases-by-visa
# ===========================================================================

class CasesByVisaItem(BaseModel):
    visa_type_id: uuid.UUID
    visa_code:    str
    visa_name:    str
    count:        int
    percentage:   float
    color_hex:    str


class CasesByVisaResponse(BaseModel):
    items: List[CasesByVisaItem]
    total: int


# ===========================================================================
# CASELOAD OVER TIME + CASE SUCCESS RATE  —  GET /analytics/caseload-over-time
# ===========================================================================

class CaseloadMonthItem(BaseModel):
    month:        str = Field(..., description="e.g. '2026-01'")
    label:        str = Field(..., description="e.g. 'Jan 2026'")
    active_cases: int


class CaseloadOverTimeResponse(BaseModel):
    months:            List[CaseloadMonthItem]
    case_success_rate: float = Field(..., description="% approved out of all closed cases")
    industry_avg_rate: float = Field(default=79.0, description="Industry benchmark — hardcoded until external data available")


# ===========================================================================
# UPCOMING ACTIONS TABLE  —  GET /analytics/upcoming-actions
# ===========================================================================

class UpcomingActionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id:        uuid.UUID
    application_id: uuid.UUID

    # Client column
    client_user_id: uuid.UUID
    client_name:    str
    client_avatar:  Optional[str] = None

    # Case column
    case_number:    str   = Field(..., examples=["#H1B-2026-041"])
    visa_code:      str   = Field(..., examples=["H1B"])

    # Action Needed
    action_title:   str

    # Due Date
    due_date:       date
    is_overdue:     bool

    # Priority
    priority:       str   = Field(..., examples=["high", "medium", "low"])


class UpcomingActionsResponse(BaseModel):
    items:  List[UpcomingActionItem]
    total:  int
    limit:  int
    offset: int
