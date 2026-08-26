"""
employee_forms_review_routes.py — attorney review actions on employee forms.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional
from fastapi import Query


from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.attorney.employee_forms_review import ApproveFormPayload, RequestCorrectionsPayload
from app.schemas.employee.employee_forms import EmployeeFormResponse, EmployeeFormListResponse,EmployeeFormVersionListResponse
from app.schemas.employee.employee_forms import CorrectionListResponse  

from app.services.attorney.employee_forms_review_service import (
    approve_form,
    list_form_versions,
    list_form_corrections ,
    list_attorney_forms,
    mark_form_completed,   
    request_corrections,
)

employee_forms_review_router = APIRouter()


@employee_forms_review_router.patch(
    "/forms/{form_type}/{form_id}/request-corrections",
    response_model=EmployeeFormResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a submitted form back to the employee for corrections",
)
async def api_request_corrections(
    form_type: str,
    form_id: uuid.UUID,
    payload: RequestCorrectionsPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeFormResponse:
    return await request_corrections(
        db, current_user.user_id, form_type, form_id,
        payload.target, payload.fields, payload.review_note,
    )


@employee_forms_review_router.patch(
    "/forms/{form_type}/{form_id}/approve",
    response_model=EmployeeFormResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a submitted form",
)
async def api_approve_form(
    form_type: str,
    form_id: uuid.UUID,
    payload: ApproveFormPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeFormResponse:
    return await approve_form(db, current_user.user_id, form_type, form_id, payload.review_note)


@employee_forms_review_router.get(
    "/forms/{form_type}/{form_id}/versions",
    response_model=EmployeeFormVersionListResponse,
    status_code=status.HTTP_200_OK,
    summary="View version history of a form",
)
async def api_list_form_versions(
    form_type: str,
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeFormVersionListResponse:
    versions = await list_form_versions(db, current_user.user_id, form_type, form_id)
    return EmployeeFormVersionListResponse(items=versions)

@employee_forms_review_router.patch(
    "/forms/{form_type}/{form_id}/complete",
    response_model=EmployeeFormResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark an approved form as fully completed",
)
async def api_mark_form_completed(
    form_type: str,
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeFormResponse:
    return await mark_form_completed(db, current_user.user_id, form_type, form_id)


@employee_forms_review_router.get(
    "/forms/{form_type}/{form_id}/corrections",
    response_model=CorrectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all correction requests for a form",
)
async def api_list_form_corrections(
    form_type: str,
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CorrectionListResponse:
    corrections = await list_form_corrections(db, current_user.user_id, form_type, form_id)
    return CorrectionListResponse(items=corrections)

@employee_forms_review_router.get(
    "/forms",
    response_model=EmployeeFormListResponse,
    status_code=status.HTTP_200_OK,
    summary="Attorney's full form queue across all assigned cases",
)
async def api_list_attorney_forms(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeFormListResponse:
    forms = await list_attorney_forms(db, current_user.user_id, status_filter, limit, offset)
    return EmployeeFormListResponse(items=forms)