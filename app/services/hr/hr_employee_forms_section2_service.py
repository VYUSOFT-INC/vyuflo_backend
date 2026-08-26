"""
hr_employee_forms_section2_service.py — HR fills Section 2 (employer
verification) of the I-9. Stored separately from the employee's Section 1
data, under form_response['section_2'], so neither party overwrites the
other's fields.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.visamodels import Application, AuditLog, EmployeeForm
from app.services.employee.services import db_create


async def hr_save_section_2(
    db: AsyncSession,
    hr_user_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
    section_2: dict,
) -> EmployeeForm:
    result = await db.execute(
        select(EmployeeForm).where(EmployeeForm.id == form_id, EmployeeForm.form_type == form_type)
    )
    form = result.scalar_one_or_none()
    if not form:
        raise NotFoundException("Form not found")

    app_result = await db.execute(select(Application).where(Application.id == form.application_id))
    application = app_result.scalar_one_or_none()
    if not application or application.assigned_hr_id != hr_user_id:
        raise ForbiddenException("You are not assigned to this case")

    if form.status in ("approved", "completed"):
        raise ConflictException("Form is finalized — cannot edit.")

    # NEW — merge into form_response without disturbing the employee's Section 1 fields
    updated_response = dict(form.form_response or {})
    updated_response["section_2"] = section_2
    form.form_response = updated_response

    form.modified_by = hr_user_id
    form.last_action_by = hr_user_id
    form.last_action_by_role = "hr"
    form.last_action_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(form)

    await db_create(db, AuditLog(
        actor_id=hr_user_id, actor_type="hr_admin", action="employee_form.hr_section2_saved",
        resource_type="employee_form", resource_id=form.id,
        description=f"form_type={form_type} section_2 updated", severity="info",
    ))
    return form