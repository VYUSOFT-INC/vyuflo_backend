
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUserData, get_current_user
from app.schemas.employee.employee_forms import (
    EmployeeFormListResponse,
    EmployeeFormResponse,
    EmployeeFormSave,
)
from app.services.employee.employee_forms_service import (
    create_or_upsert_employee_form,
    list_employee_forms,
    get_employee_form_by_id, 
    _get_open_corrections, 
    save_employee_form_draft,
    submit_employee_form,
)

employee_forms_router = APIRouter()


@employee_forms_router.get(
    "/employee/forms/{form_type}",
    response_model=EmployeeFormListResponse,
    status_code=status.HTTP_200_OK,
    summary="List my forms of a given type (I-9, I-983, ...)",
)
async def api_list_employee_forms(
    form_type: str,
    application_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
) -> EmployeeFormListResponse:
    forms = await list_employee_forms(db, current_user.user_id, form_type, application_id)
    return EmployeeFormListResponse(items=forms)


@employee_forms_router.post(
    "/employee/forms/{form_type}",
    response_model=EmployeeFormResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or upsert a draft form (first save)",
)
async def api_create_or_upsert_employee_form(
    form_type: str,
    payload: EmployeeFormSave,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
) -> EmployeeFormResponse:
    return await create_or_upsert_employee_form(db, current_user.user_id, form_type, payload)


@employee_forms_router.put(
    "/employee/forms/{form_type}/{form_id}",
    response_model=EmployeeFormResponse,
    status_code=status.HTTP_200_OK,
    summary="Save draft — used by 'Draft' AND 'Save & Continue' buttons",
)
async def api_save_employee_form_draft(
    form_type: str,
    form_id: uuid.UUID,
    payload: EmployeeFormSave,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
) -> EmployeeFormResponse:
    return await save_employee_form_draft(db, current_user.user_id, form_type, form_id, payload)


@employee_forms_router.post(
    "/employee/forms/{form_type}/{form_id}/submit",
    response_model=EmployeeFormResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit + lock the form",
)
async def api_submit_employee_form(
    form_type: str,
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
) -> EmployeeFormResponse:
    return await submit_employee_form(db, current_user.user_id, form_type, form_id)

@employee_forms_router.get(
    "/employee/forms/{form_type}/{form_id}",
    response_model=EmployeeFormResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single form by ID — used by Editor and Preview screens",
)

async def api_get_employee_form(
    form_type: str,
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
) -> EmployeeFormResponse:
    form = await get_employee_form_by_id(db, current_user.user_id, form_type, form_id)
    response = EmployeeFormResponse.model_validate(form)               # NEW
    response.open_corrections = await _get_open_corrections(db, form.id)  # NEW
    return response