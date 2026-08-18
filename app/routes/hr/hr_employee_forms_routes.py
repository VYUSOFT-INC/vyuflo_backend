
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.employee.employee_forms import EmployeeFormListResponse
from app.services.employee.employee_forms_service import hr_list_employee_forms

hr_employee_forms_router = APIRouter()

@hr_employee_forms_router.get(
    "/forms/{form_type}",
    response_model=EmployeeFormListResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: view an employee's forms for a case (I-9, I-983, ...) — only if assigned to that case",
)
async def api_hr_list_employee_forms(
    form_type: str,
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeFormListResponse:
    forms = await hr_list_employee_forms(db, current_user.user_id, form_type, application_id)  # CHANGED — passes current_user.user_id
    return EmployeeFormListResponse(items=forms)
