# app/schemas/hr/hr_case_overview_schemas.py
#
# Combined response for the HR Case Detail → "Overview" tab.
# This does NOT re-declare case/deadline fields — it composes the existing
# HRCaseResponse and DeadlineItemResponse schemas so there is one response
# shape to keep in sync instead of three.

from typing import List

from pydantic import BaseModel, ConfigDict

from app.schemas.hr.hr_case_schemas import HRCaseResponse
from app.schemas.hr.hr_deadline_schemas import DeadlineItemResponse


class HRCaseQuickStats(BaseModel):
    """
    Powers the "Quick Stats" card:
      Documents  → documents_completed / documents_total
      Approvals  → approvals_completed / approvals_total
      Progress   → progress_percent / 100
    """
    documents_completed:  int
    documents_total:      int
    approvals_completed:  int
    approvals_total:      int
    progress_percent:     int

    model_config = ConfigDict(from_attributes=True)


class HRCaseOverviewResponse(BaseModel):
    """
    GET /hr/cases/{application_id}/overview

    Single payload for the Overview tab: Case Header + Case Summary +
    Employment Details + Internal Notes (via `case`), Quick Stats
    (via `quick_stats`), and the Upcoming Deadlines widget (via
    `upcoming_deadlines`, capped to the 3 nearest non-completed deadlines).
    """
    case:               HRCaseResponse
    quick_stats:        HRCaseQuickStats
    upcoming_deadlines: List[DeadlineItemResponse]

    model_config = ConfigDict(from_attributes=True)
