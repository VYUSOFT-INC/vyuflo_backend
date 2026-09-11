from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUserData, get_current_user
from app.schemas.attorney.new_case_schemas import (
    AttorneyTaskCreateRequest,
    AttorneyTaskListResponse,
    AttorneyTaskResponse,
    CompleteAttorneyTaskRequest,
    NewCaseCreateRequest,
    NewCaseCreateResponse,
    ConsultedClientOut,
    FileCaseRequest,
    FileCaseResponse,
    RecordFilingRequest,
    FilingResponse,
    FilingListResponse,
)
from app.schemas.attorney.payment_status import PaymentStatusCreate, PaymentStatusListResponse, PaymentStatusResponse
from app.services.attorney.new_case_service import (
    attorney_create_task,
    create_lawyer_case,
    list_consulted_clients,
    file_case,
    record_filing,
    list_filings,
    list_attorney_tasks,
    complete_attorney_task,
)
from app.services.attorney.payment_status_service import attorney_mark_payment_in_progress, list_payment_statuses_for_case

new_case_router = APIRouter(tags=["Lawyer New Case"])


def _require_attorney(current_user: CurrentUserData) -> None:
    if "attorney" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only attorneys can create cases from the marketplace wizard.",
        )


@new_case_router.post(
    "/lawyer/cases",
    response_model=NewCaseCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attorney creates a new case for a consulted client",
)
async def api_create_lawyer_case(
    body: NewCaseCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    result = await create_lawyer_case(db, body, attorney_user_id=current_user.user_id)
    await db.commit()
    return result


@new_case_router.get(
    "/lawyer/consulted-clients",
    response_model=List[ConsultedClientOut],
    summary="List clients this attorney has completed a consultation with",
)
async def api_list_consulted_clients(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    return await list_consulted_clients(db, attorney_user_id=current_user.user_id)


@new_case_router.patch(
    "/lawyer/applications/{application_id}/file",
    response_model=FileCaseResponse,
    summary="Attorney records receipt number + priority date once a case is filed",
)
async def api_file_case(
    application_id: uuid.UUID,
    body: FileCaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    result = await file_case(db, application_id, body, attorney_user_id=current_user.user_id)
    await db.commit()
    return result


# =============================================================================
# NEW — record/list government filings (LCA, petition, RFE response, appeal).
# =============================================================================

@new_case_router.post(
    "/lawyer/applications/{application_id}/filings",
    response_model=FilingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attorney records a government filing (LCA, petition, RFE response, appeal)",
)
async def api_record_filing(
    application_id: uuid.UUID,
    body: RecordFilingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    result = await record_filing(db, application_id, body, attorney_user_id=current_user.user_id)
    await db.commit()
    return result


@new_case_router.get(
    "/lawyer/applications/{application_id}/filings",
    response_model=FilingListResponse,
    summary="List all government filings recorded for a case",
)
async def api_list_filings(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    return await list_filings(db, application_id, user_id=current_user.user_id)


@new_case_router.get(
    "/lawyer/applications/{application_id}/tasks",
    response_model=AttorneyTaskListResponse,
    summary="List documents HR has requested from the attorney on this case",
)
async def api_list_attorney_tasks(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    return await list_attorney_tasks(db, application_id, attorney_user_id=current_user.user_id)
 
 
@new_case_router.patch(
    "/lawyer/applications/{application_id}/tasks/{task_id}/complete",
    response_model=AttorneyTaskResponse,
    summary="Attorney marks a document request fulfilled after uploading the file",
)
async def api_complete_attorney_task(
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    body: CompleteAttorneyTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    result = await complete_attorney_task(db, application_id, task_id, body, attorney_user_id=current_user.user_id)
    await db.commit()
    return result

@new_case_router.post(
    "/lawyer/applications/{application_id}/tasks",
    response_model=AttorneyTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attorney creates an intake task — routed through HR before reaching the employee",
)
async def api_attorney_create_task(
    application_id: uuid.UUID,
    body: AttorneyTaskCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    result = await attorney_create_task(db, application_id, body, attorney_user_id=current_user.user_id)
    await db.commit()
    return result

@new_case_router.post(
    "/lawyer/applications/{application_id}/payment-status",
    response_model=PaymentStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attorney marks a payment as currently in progress (before a real filing exists)",
)
async def api_mark_payment_in_progress(
    application_id: uuid.UUID,
    body: PaymentStatusCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    result = await attorney_mark_payment_in_progress(db, application_id, body, attorney_user_id=current_user.user_id)
    await db.commit()
    return result
 
 
@new_case_router.get(
    "/lawyer/applications/{application_id}/payment-status",
    response_model=PaymentStatusListResponse,
    summary="List payment status updates recorded for a case (attorney or HR)",
)
async def api_list_payment_statuses(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    return await list_payment_statuses_for_case(db, application_id, user_id=current_user.user_id)