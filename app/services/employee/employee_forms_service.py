
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, ConflictException, NotFoundException
from app.models.visamodels import Application, AuditLog, EmployeeForm, Notification
from app.schemas.employee.employee_forms import EmployeeFormSave
from app.services.employee.services import db_create


async def list_employee_forms(
    db: AsyncSession,
    employee_id: uuid.UUID,
    form_type: str,
    application_id: Optional[uuid.UUID] = None,
) -> list[EmployeeForm]:
    query = select(EmployeeForm).where(
        EmployeeForm.employee_id == employee_id,
        EmployeeForm.form_type == form_type,
    )
    if application_id:
        query = query.where(EmployeeForm.application_id == application_id)

    result = await db.execute(query)
    return list(result.scalars().all())

async def get_employee_form_by_id(
    db: AsyncSession,
    employee_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
) -> EmployeeForm:
    """Used by the Editor and Preview screens — fetch one form by its own ID."""
    return await _get_owned_form(db, employee_id, form_type, form_id)

async def create_or_upsert_employee_form(
    db: AsyncSession,
    employee_id: uuid.UUID,
    form_type: str,
    payload: EmployeeFormSave,
) -> EmployeeForm:
    """
    Manager confirmed: 'update it' — if a draft already exists for this
    (application_id, form_type), overwrite it. Never throw 409 here.
    """
    if not payload.application_id:
        raise ConflictException("application_id is required to create a form")

    result = await db.execute(
        select(EmployeeForm).where(
            EmployeeForm.application_id == payload.application_id,
            EmployeeForm.form_type == form_type,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.status == "submitted":
            raise ConflictException("Form already submitted — cannot edit.")
        existing.form_response = payload.form_response
        existing.modified_by = employee_id
        await db.flush()
        await db.refresh(existing)
        await _log_form_event(db, existing, employee_id, "employee_form.saved")
        return existing

    new_form = EmployeeForm(
        application_id=payload.application_id,
        employee_id=employee_id,
        form_type=form_type,
        status="draft",
        form_response=payload.form_response,
        created_by=employee_id,
        modified_by=employee_id,
    )
    new_form = await db_create(db, new_form)
    await _log_form_event(db, new_form, employee_id, "employee_form.saved")
    return new_form


async def save_employee_form_draft(
    db: AsyncSession,
    employee_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
    payload: EmployeeFormSave,
) -> EmployeeForm:
    """Used by both the 'Draft' button and 'Save & Continue' button."""
    form = await _get_owned_form(db, employee_id, form_type, form_id)

    if form.status == "submitted":
        raise ConflictException("Form is locked — already submitted.")

    form.form_response = payload.form_response
    form.modified_by = employee_id
    await db.flush()
    await db.refresh(form)
    await _log_form_event(db, form, employee_id, "employee_form.saved")
    return form


async def submit_employee_form(
    db: AsyncSession,
    employee_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
) -> EmployeeForm:
    form = await _get_owned_form(db, employee_id, form_type, form_id)

    if form.status == "submitted":
        raise ConflictException("Already submitted.")

    form.status = "submitted"
    form.submitted_at = datetime.now(timezone.utc)
    form.modified_by = employee_id
    await db.flush()
    await db.refresh(form)
    await _log_form_event(db, form, employee_id, "employee_form.submitted")

    # Notify the assigned attorney — best-effort, doesn't block the submit
    app_result = await db.execute(select(Application).where(Application.id == form.application_id))
    application = app_result.scalar_one_or_none()
    if application and application.assigned_attorney_id:
        notification = Notification(
            user_id=application.assigned_attorney_id,
            notification_type="case_status_updated",
            category="case_update",
            priority="medium",
            title=f"Client submitted their {form_type.upper()}",
            body=f"Your client has submitted Form {form_type.upper()} for case {application.application_number}.",
            application_id=application.id,
            actor_id=employee_id,
            cta_primary_label="Review form",
            cta_primary_url=f"/lawyer/applications/{application.id}/forms/{form_type}",
            created_by=employee_id,
        )
        await db_create(db, notification)

    return form


# =============================================================================
# HR read-only access (manager confirmed: HR can view forms)
# =============================================================================

async def hr_list_employee_forms(
    db: AsyncSession,
    hr_user_id: uuid.UUID,         
    form_type: str,
    application_id: uuid.UUID,
) -> list[EmployeeForm]:
    app_result = await db.execute(select(Application).where(Application.id == application_id))
    application = app_result.scalar_one_or_none()

    if not application:                                       
        raise NotFoundException("Case not found")
    if application.assigned_hr_id != hr_user_id:                
        raise ForbiddenException("You are not assigned to this case")
    result = await db.execute(
        select(EmployeeForm).where(
            EmployeeForm.application_id == application_id,
            EmployeeForm.form_type == form_type,
        )
    )
    return list(result.scalars().all())


# =============================================================================
# Internal helpers
# =============================================================================

async def _get_owned_form(
    db: AsyncSession,
    employee_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
) -> EmployeeForm:
    result = await db.execute(
        select(EmployeeForm).where(
            EmployeeForm.id == form_id,
            EmployeeForm.form_type == form_type,
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise NotFoundException("Form not found")
    if form.employee_id != employee_id:
        raise ForbiddenException("Not your form")
    return form


async def _log_form_event(
    db: AsyncSession,
    form: EmployeeForm,
    actor_id: uuid.UUID,
    action: str,
) -> None:
    """Lightweight audit trail, per the original doc's Section 4."""
    log = AuditLog(
        actor_id=actor_id,
        actor_type="user",
        action=action,
        resource_type="employee_form",
        resource_id=form.id,
        description=f"application_id={form.application_id} form_type={form.form_type} status={form.status}",
        severity="info",
    )
    await db_create(db, log)