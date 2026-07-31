# app/routes/hr_case_overview_routes.py
#
# HR Case Detail — "Overview" tab aggregator.
# Kept as its own router (rather than added to hr_case_routes.py) so it can
# be mounted/reviewed independently of the hr_case_service.py fix.
#
# Mount in main.py ALONGSIDE hr_case_router:
#   from app.routes.hr_case_overview_routes import hr_case_overview_router
#   app.include_router(hr_case_overview_router, prefix="/api/v1/hr", tags=["HR Case Overview"])
#
# Endpoint:
#   GET /api/v1/hr/cases/{application_id}/overview

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.hr.hr_case_overview_schemas import HRCaseOverviewResponse
from app.services.hr.hr_case_overview_service import hr_get_case_overview

hr_case_overview_router = APIRouter()


@hr_case_overview_router.get(
    "/cases/{application_id}/overview",
    response_model=HRCaseOverviewResponse,
    summary="HR: Combined Overview tab payload (header + quick stats + upcoming deadlines)",
    description="""
Single call for the Case Detail → Overview tab, composed entirely from
existing services (no duplicated business logic):

- `case`               → hr_case_service.hr_get_case
                          (Case Header, Case Summary, Employment Details,
                          Internal Notes, Overall Progress)
- `quick_stats`        → hr_task_service.hr_list_tasks (Documents X/Y) +
                          hr_approval_service.hr_list_approvals (Approvals X/Y,
                          case-scoped) + case.progress_percent (Progress)
- `upcoming_deadlines` → hr_deadline_service.hr_list_deadlines
                          (case-scoped, top 3 by due_date)

Requires `hr_case_service.py` to be restored (see backend audit — it is
currently fully commented out in the codebase as uploaded).
    """,
)
async def api_hr_get_case_overview(
    application_id: uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> HRCaseOverviewResponse:
    return await hr_get_case_overview(db, application_id, current_user.user_id)
