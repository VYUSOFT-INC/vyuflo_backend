"""
hr_employee_forms_review_routes.py — HR review actions on employee forms:
send back for corrections, or approve + forward to attorney.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Query

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.attorney.employee_forms_review import ApproveFormPayload, RequestCorrectionsPayload
from app.schemas.employee.employee_forms import EmployeeFormResponse,EmployeeFormListResponse, HRSection2Save
from app.services.hr.hr_employee_forms_section2_service import hr_save_section_2  
from app.services.hr.hr_employee_forms_review_service import (
    hr_approve_and_forward,
    hr_list_action_items,
    hr_request_corrections,
)

hr_employee_forms_review_router = APIRouter()


@hr_employee_forms_review_router.patch(
    "/forms/{form_type}/{form_id}/request-corrections",
    response_model=EmployeeFormResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: send a submitted form back to the employee for corrections",
)
async def api_hr_request_corrections(
    form_type: str,
    form_id: uuid.UUID,
    payload: RequestCorrectionsPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeFormResponse:
    return await hr_request_corrections(
        db, current_user.user_id, form_type, form_id,
        payload.fields, payload.review_note,
    )


@hr_employee_forms_review_router.patch(
    "/forms/{form_type}/{form_id}/approve",
    response_model=EmployeeFormResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: approve and forward a form to the attorney",
)
async def api_hr_approve_and_forward(
    form_type: str,
    form_id: uuid.UUID,
    payload: ApproveFormPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeFormResponse:
    return await hr_approve_and_forward(db, current_user.user_id, form_type, form_id, payload.review_note)



@hr_employee_forms_review_router.put(
    "/forms/{form_type}/{form_id}/section-2",
    response_model=EmployeeFormResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: save Section 2 (employer verification)",
)
async def api_hr_save_section_2(
    form_type: str,
    form_id: uuid.UUID,
    payload: HRSection2Save,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeFormResponse:
    return await hr_save_section_2(db, current_user.user_id, form_type, form_id, payload.section_2)

@hr_employee_forms_review_router.get(
    "/action-items",
    response_model=EmployeeFormListResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: forms waiting on my review — dashboard Action Items card",
)
async def api_hr_list_action_items(
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeFormListResponse:
    forms = await hr_list_action_items(db, current_user.user_id, limit)
    return EmployeeFormListResponse(items=forms)