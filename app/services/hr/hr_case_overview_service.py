# app/services/hr/hr_case_overview_service.py
"""
Aggregator for the HR Case Detail → "Overview" tab.

Per the backend audit: the Overview tab needs data that already lives in
three separate, working services. This module does NOT reimplement any of
that logic — it calls the existing services and reshapes their output.

Composes:
  hr_case_service.hr_get_case          → Case Header, Case Summary,
                                          Employment Details, Internal Notes,
                                          Progress %. Also performs the
                                          HR-ownership check for this whole
                                          aggregator (raises 404/403 first).
  hr_task_service.hr_list_tasks        → Documents quick-stat
                                          (required vs. completed checklist items)
  hr_approval_service.hr_list_approvals → Approvals quick-stat, scoped to
                                          this single case via the new
                                          `application_id` filter
  hr_deadline_service.hr_list_deadlines → Upcoming Deadlines widget, scoped
                                          to this single case via the new
                                          `application_id` filter

IMPORTANT DEPENDENCY: hr_get_case is imported from hr_case_service.py.
Per the audit, that file is currently fully commented out in the uploaded
codebase — this aggregator will raise an ImportError until it's restored.
This module makes no attempt to work around that; fixing hr_case_service.py
is a separate, required task.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.hr.hr_case_service import hr_get_case
from app.services.hr.hr_task_service import hr_list_tasks
from app.services.hr.hr_approval_service import hr_list_approvals
from app.services.hr.hr_deadline_service import hr_list_deadlines
from app.schemas.hr.hr_approval_schemas import ApprovalItemStatus
from app.schemas.hr.hr_case_overview_schemas import (
    HRCaseOverviewResponse,
    HRCaseQuickStats,
)

UPCOMING_DEADLINES_LIMIT = 3


async def hr_get_case_overview(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> HRCaseOverviewResponse:
    # ── Case Header / Case Summary / Employment Details / Internal Notes ─────
    # hr_get_case() -> _assert_hr_owns_case() also does the 403/404 ownership
    # check for this entire endpoint, so nothing else below needs to repeat it.
    case = await hr_get_case(db, application_id, hr_user_id)

    # ── Documents quick-stat ──────────────────────────────────────────────────
    # Reuses the checklist that hr_task_service already builds (auto-created
    # from visa_type.required_documents + any custom HR tasks).
    tasks = await hr_list_tasks(db, application_id, hr_user_id)
    required_tasks = [t for t in tasks if t.is_required]
    documents_total = len(required_tasks)
    documents_completed = sum(1 for t in required_tasks if t.is_completed)

    # ── Approvals quick-stat ──────────────────────────────────────────────────
    # Case-scoped call to the existing approval queue service (see the new
    # `application_id` param added to hr_list_approvals).
    approvals = await hr_list_approvals(
        db=db,
        hr_user_id=hr_user_id,
        application_id=application_id,
        status="all",
    )
    approvals_total = approvals.total
    approvals_completed = sum(
        1 for item in approvals.items if item.status == ApprovalItemStatus.approved
    )

    # ── Upcoming Deadlines widget ──────────────────────────────────────────────
    # Case-scoped call to the existing deadlines service (see the new
    # `application_id` param added to hr_list_deadlines). Already ordered by
    # due_date ascending — just cap to the top N for the widget.
    deadlines = await hr_list_deadlines(
        db=db,
        hr_user_id=hr_user_id,
        application_id=application_id,
    )
    upcoming_deadlines = deadlines.items[:UPCOMING_DEADLINES_LIMIT]

    quick_stats = HRCaseQuickStats(
        documents_completed  = documents_completed,
        documents_total      = documents_total,
        approvals_completed  = approvals_completed,
        approvals_total      = approvals_total,
        progress_percent     = case.progress_percent,
    )

    return HRCaseOverviewResponse(
        case               = case,
        quick_stats        = quick_stats,
        upcoming_deadlines = upcoming_deadlines,
    )
