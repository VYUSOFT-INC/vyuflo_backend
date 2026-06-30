"""
lawyer_dashboard_schema.py — Pydantic schemas for 25 - Lawyer Dashboard.

"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# KPI CARDS — top row (4 cards)
# ===========================================================================

class DashboardKpiCards(BaseModel):
    """
    Powers the 4 KPI stat cards at the top of Screen 25.

    active_cases:
      Applications WHERE assigned_attorney_id=current AND status IN
      ('in_progress','action_needed','rfe_response').
      active_cases_delta_week → "+4 this week" subtitle.

    unbilled_hours + unbilled_amount_cents:
      TimeEntry WHERE attorney_id=current AND status='unbilled'.
      Shown as "47.5 hrs" + "$16,625 unbilled".

    deadlines_today:
      Deadline WHERE user_id=current AND due_date=today
      AND is_completed=False AND is_dismissed=False.
      requires_action=True → "Requires immediate action" label.

    new_client_intakes:
      Application WHERE assigned_attorney_id=current AND status='draft'
      AND created_at >= (now - 30 days).
      Shown as "8" + "Pending review" subtitle.
    """
    # Card 1 — Active Cases
    active_cases:            int
    active_cases_delta_week: int   = Field(
        0, description="Change vs 7 days ago. e.g. 4 → '+4 this week'",
    )

    # Card 2 — Unbilled Hours
    unbilled_hours:        float  = Field(..., description="e.g. 47.5")
    unbilled_amount_cents: int    = Field(..., description="e.g. 1662500 = $16,625")

    # Card 3 — Deadlines Today
    deadlines_today:  int
    requires_action:  bool = Field(
        False,
        description="True when deadlines_today > 0 → 'Requires immediate action' label",
    )

    # Card 4 — New Client Intakes
    new_client_intakes: int
    pending_review:     int = Field(
        0, description="Same value — shown as 'Pending review' subtitle",
    )


# ===========================================================================
# RECENT CASES TABLE
# ===========================================================================

class RecentCaseItem(BaseModel):
    """
    One row in the Recent Cases table.

    Screen 25 columns:
      CLIENT          CASE TYPE   STATUS           NEXT ACTION
      TechCorp Inc.   H-1B        In Progress      Submit LCA
      Elena Rodriguez O-1A        Action Required  Review RFE Response
      Global Logistics L-1A       In Progress      Draft Support Letter
    """
    model_config = ConfigDict(from_attributes=True)

    application_id:     uuid.UUID
    application_number: str

    # CLIENT column
    client_name:       str
    client_avatar_url: Optional[str] = None

    # CASE TYPE column
    visa_type_code: str   # "H-1B", "O-1A", "L-1A"

    # STATUS column
    status:       str   # raw enum: "in_progress" | "action_needed" etc.
    status_label: str   # display: "In Progress" | "Action Required"

    # NEXT ACTION column — first incomplete ApplicationTask.task_name
    next_action: Optional[str] = None   # "Submit LCA", "Draft Support Letter"

    updated_at: datetime


class RecentCasesResponse(BaseModel):
    """Response for GET /lawyer-dashboard/recent-cases."""
    items: List[RecentCaseItem]
    total: int


# ===========================================================================
# MONTHLY BILLING PANEL — right sidebar
# ===========================================================================

class MonthlyBillingResponse(BaseModel):
    """
    Powers the Monthly Billing panel on Screen 25.

    monthly_billed_cents:
      AttorneyInvoice WHERE attorney_id=current AND status IN ('sent','paid')
      AND issued_date in current month. Shown as "$12,450".

    mom_change_pct:
      (this_month - last_month) / last_month * 100. e.g. 8.0 → "+8%".
      mom_positive=True → green arrow, False → red arrow.

    target_cents:
      attorney_profiles.monthly_billing_target_cents.
      Shown as "Target: $15,000". None = target not set, hide progress bar.

    target_pct:
      monthly_billed_cents / target_cents * 100 → "83%" progress bar.
      None if no target set.

    billed_hours:
      TimeEntry WHERE status IN ('invoiced','paid') AND current month. → "35.5".

    unbilled_hours:
      TimeEntry WHERE status='unbilled'. → "47.5" shown in orange.
    """
    monthly_billed_cents: int   = Field(..., description="e.g. 1245000 = $12,450")
    mom_change_pct:       float = Field(..., description="e.g. 8.0 → '+8%'")
    mom_positive:         bool  = Field(..., description="True = green arrow")

    target_cents: Optional[int]   = Field(
        None,
        description="attorney_profiles.monthly_billing_target_cents. None = not set.",
    )
    target_pct:   Optional[float] = Field(
        None,
        description="Progress towards target. None if no target set.",
    )

    billed_hours:   float = Field(..., description="e.g. 35.5")
    unbilled_hours: float = Field(..., description="e.g. 47.5 — shown in orange")


# ===========================================================================
# FULL DASHBOARD RESPONSE — single aggregated endpoint
# ===========================================================================

class LawyerDashboardResponse(BaseModel):
    """
    GET /lawyer-dashboard — full Screen 25 payload in one call.

    Today's Schedule and Critical Deadlines are NOT included here.
    They use existing endpoints (no duplication):
      GET /calendar/agenda     → Today's Schedule panel (left)
      GET /calendar/deadlines  → Critical Deadlines sidebar (right)
    """
    attorney_first_name: str
    attorney_role:       Optional[str] = None   # "Senior Partner"
    greeting_date:       date                   # "Tuesday, 14 April 2026"

    kpi_cards:       DashboardKpiCards
    recent_cases:    RecentCasesResponse
    monthly_billing: MonthlyBillingResponse
