# app/routes/hr_case_routes.py
"""
FastAPI router for HR-initiated case management.

Mount in main.py:
    from app.routes.hr_case_routes import hr_case_router
    app.include_router(hr_case_router, prefix="/api/v1/hr", tags=["HR Cases"])

Resulting endpoints:
    POST   /api/v1/hr/cases                              — create case
    GET    /api/v1/hr/cases                              — list all HR's cases
    GET    /api/v1/hr/cases/{application_id}             — get single case
    PATCH  /api/v1/hr/cases/{application_id}             — update case fields
    PATCH  /api/v1/hr/cases/{application_id}/status      — change status (+ history)
    PATCH  /api/v1/hr/cases/{application_id}/hr-approval — HR approve/reject
    GET    /api/v1/hr/cases/{application_id}/history     — status timeline
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User
from app.schemas.hr.hr_case_schemas import (
    HRApprovalUpdate,
    HRCaseCreate,
    HRCaseCreateResponse,
    HRCaseListQuery,
    HRCaseListResponse,
    HRCaseResponse,
    HRCaseStatusHistoryResponse,
    HRCaseStatusUpdate,
    HRCaseUpdate,
)
from app.services.hr.hr_case_service import (
    hr_create_case,
    hr_get_case,
    hr_list_case_history,
    hr_list_cases,
    hr_update_approval,
    hr_update_case,
    hr_update_case_status,
)

hr_case_router = APIRouter()


# =============================================================================
# CREATE
# =============================================================================

@hr_case_router.post(
    "/cases",
    response_model=HRCaseCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="HR: Create immigration case for an employee",
    description="""
HR creates a new immigration case on behalf of a linked employee.

**Key differences from the employee POST /applications endpoint:**
- `employee_link_id` identifies which of HR's roster employees to sponsor
- `visa_type_code` ("H-1B", "L-1A", etc.) is resolved server-side to the UUID
- `assigned_hr_id` is automatically set to the current HR user — client never sends it
- Duplicate check is per employee + visa type (not per logged-in user)
- Case immediately activates to `profile_eligibility` stage
- Document checklist tasks are auto-created from `visa_types.required_documents`
    """,
)
async def create_hr_case(
    payload:      HRCaseCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
) -> HRCaseCreateResponse:
    return await hr_create_case(db, payload, current_user.user_id)


# =============================================================================
# LIST
# =============================================================================

@hr_case_router.get(
    "/cases",
    response_model=HRCaseListResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: List all cases assigned to me",
    description="""
Returns all `applications` where `assigned_hr_id` = current HR user.

Includes KPI summary cards (total_active, action_needed, approved_ytd,
expiring_soon) computed across ALL of HR's cases regardless of filters.
Filtered results honour the optional query params.
    """,
)
async def list_hr_cases(
    status:           Optional[str]       = Query(None, description="Filter by status"),
    visa_type_code:   Optional[str]       = Query(None, description="Filter by visa code e.g. H-1B"),
    employee_user_id: Optional[uuid.UUID] = Query(None, description="Filter by employee"),
    attorney_user_id: Optional[uuid.UUID] = Query(None, description="Filter by attorney"),
    limit:            int                  = Query(50, ge=1, le=200),
    offset:           int                  = Query(0,  ge=0),
    db:               AsyncSession         = Depends(get_db),
    current_user:     User                 = Depends(get_current_user),
) -> HRCaseListResponse:
    query = HRCaseListQuery(
        status           = status,
        visa_type_code   = visa_type_code,
        employee_user_id = employee_user_id,
        attorney_user_id = attorney_user_id,
        limit            = limit,
        offset           = offset,
    )
    return await hr_list_cases(db, current_user.user_id, query)


# =============================================================================
# GET SINGLE
# =============================================================================

@hr_case_router.get(
    "/cases/{application_id}",
    response_model=HRCaseResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: Get a single case by ID",
    description="Returns the full case detail. 403 if the case is not assigned to the current HR user.",
)
async def get_hr_case(
    application_id: uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user:   User         = Depends(get_current_user),
) -> HRCaseResponse:
    return await hr_get_case(db, application_id, current_user.user_id)


# =============================================================================
# UPDATE CASE FIELDS
# =============================================================================

@hr_case_router.patch(
    "/cases/{application_id}",
    response_model=HRCaseResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: Update case fields",
    description="""
Partial update of case metadata. Send only the fields you want to change.

Updatable fields: `case_name`, `case_description`, `target_date`,
`priority`, `internal_notes`, `attorney_user_id`, `sponsor_employer`,
`has_action_required`, `action_required_note`.

To change `status` use the dedicated `/status` sub-endpoint (creates a history record).
    """,
)
async def update_hr_case(
    application_id: uuid.UUID,
    payload:        HRCaseUpdate,
    db:             AsyncSession = Depends(get_db),
    current_user:   User         = Depends(get_current_user),
) -> HRCaseResponse:
    return await hr_update_case(db, application_id, payload, current_user.user_id)


# =============================================================================
# UPDATE STATUS
# =============================================================================

@hr_case_router.patch(
    "/cases/{application_id}/status",
    response_model=HRCaseResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: Change case status (appends history record)",
    description="""
Dedicated status-change endpoint. Always appends an immutable row to
`application_status_history` and fires status-change notifications to the
employee, attorney (if assigned), and the HR user.

Valid transitions HR can trigger:
  in_progress → action_needed, submitted, withdrawn
  action_needed → in_progress, submitted
  rfe_response → submitted
  submitted → approved, rejected, withdrawn
    """,
)
async def update_hr_case_status(
    application_id: uuid.UUID,
    payload:        HRCaseStatusUpdate,
    db:             AsyncSession = Depends(get_db),
    current_user:   User         = Depends(get_current_user),
) -> HRCaseResponse:
    return await hr_update_case_status(db, application_id, payload, current_user.user_id)


# =============================================================================
# HR APPROVAL
# =============================================================================

@hr_case_router.patch(
    "/cases/{application_id}/hr-approval",
    response_model=HRCaseResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: Set approval status on a case",
    description="""
HR formally reviews and approves/rejects/requests changes before attorney
filing. Sets `hr_approval_status`, `hr_notes`, `hr_approved_at`,
`hr_approved_by` on the Application row.

Fires an in-app notification to the employee.

Allowed values for `hr_approval_status`:
  pending | approved | rejected | changes_requested
    """,
)
async def update_hr_approval(
    application_id: uuid.UUID,
    payload:        HRApprovalUpdate,
    db:             AsyncSession = Depends(get_db),
    current_user:   User         = Depends(get_current_user),
) -> HRCaseResponse:
    return await hr_update_approval(db, application_id, payload, current_user.user_id)


# =============================================================================
# STATUS HISTORY
# =============================================================================

@hr_case_router.get(
    "/cases/{application_id}/history",
    response_model=List[HRCaseStatusHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="HR: Get status history timeline for a case",
    description="""
Returns the immutable `application_status_history` rows for this case
in chronological order (oldest first). Used to render the timeline
in the HR Case Detail screen.
    """,
)
async def get_hr_case_history(
    application_id: uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user:   User         = Depends(get_current_user),
) -> List[HRCaseStatusHistoryResponse]:
    return await hr_list_case_history(db, application_id, current_user.user_id)