"""
hr_employee_forms_review_service.py — HR reviews a submitted employee form:
either sends it back for corrections, or forwards it to the attorney.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.visamodels import Application, AuditLog, EmployeeForm, FormCorrection,Notification
from app.services.employee.services import db_create


async def hr_request_corrections(
    db: AsyncSession,
    hr_user_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
    fields: list[str],        
    review_note: str,
) -> EmployeeForm:
    form, application = await _get_form_for_hr(db, hr_user_id, form_type, form_id)

    if form.status != "submitted":
        raise ConflictException("Only a submitted form can be sent back for corrections.")

    form.status = "needs_corrections"
    form.review_note = review_note
    form.reviewed_by = hr_user_id
    form.reviewed_at = datetime.now(timezone.utc)
    form.last_action_by = hr_user_id
    form.last_action_by_role = "hr"
    form.last_action_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(form)

     # NEW — create the actual correction record (HR always targets the employee)
    await db_create(db, FormCorrection(
        form_type=form_type,
        form_id=form.id,
        target="employee",   # HR corrections always go back to the employee
        fields=fields,
        note=review_note,
        requested_by=hr_user_id,
    ))

    await db_create(db, Notification(
        user_id=form.employee_id,
        notification_type="case_status_updated",
        category="case_update",
        priority="high",
        title=f"Your {form_type.upper()} needs corrections",
        body=review_note,
        application_id=form.application_id,
        actor_id=hr_user_id,
        cta_primary_label="Fix and resubmit",
        cta_primary_url=f"/employee/forms/{form_type}/{form.id}",
        created_by=hr_user_id,
    ))
    await db_create(db, AuditLog(
        actor_id=hr_user_id, actor_type="hr_admin", action="employee_form.hr_corrections_requested",
        resource_type="employee_form", resource_id=form.id, description=review_note, severity="info",
    ))
    return form


async def hr_approve_and_forward(
    db: AsyncSession,
    hr_user_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
    review_note: str | None,
) -> EmployeeForm:
    form, application = await _get_form_for_hr(db, hr_user_id, form_type, form_id)

    if form.status != "submitted":
        raise ConflictException("Only a submitted form can be forwarded to the attorney.")

    form.status = "hr_approved"
    form.review_note = review_note
    form.reviewed_by = hr_user_id
    form.reviewed_at = datetime.now(timezone.utc)
    form.last_action_by = hr_user_id
    form.last_action_by_role = "hr"
    form.last_action_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(form)

    if application.assigned_attorney_id:
        await db_create(db, Notification(
            user_id=application.assigned_attorney_id,
            notification_type="case_status_updated",
            category="case_update",
            priority="medium",
            title=f"{form_type.upper()} ready for your review",
            body=f"HR has reviewed and forwarded Form {form_type.upper()} for case {application.application_number}.",
            application_id=application.id,
            actor_id=hr_user_id,
            cta_primary_label="Review form",
            cta_primary_url=f"/lawyer/applications/{application.id}/forms/{form_type}",
            created_by=hr_user_id,
        ))
    await db_create(db, AuditLog(
        actor_id=hr_user_id, actor_type="hr_admin", action="employee_form.hr_approved_forwarded",
        resource_type="employee_form", resource_id=form.id, description=review_note, severity="info",
    ))
    return form


async def _get_form_for_hr(db, hr_user_id, form_type, form_id):
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

    return form, application

async def hr_list_action_items(
    db: AsyncSession,
    hr_user_id: uuid.UUID,
    limit: int = 25,
) -> list[EmployeeForm]:
    """Forms sitting in HR's queue, waiting on action — the Action Items card."""
    result = await db.execute(
        select(EmployeeForm)
        .join(Application, Application.id == EmployeeForm.application_id)
        .where(
            Application.assigned_hr_id == hr_user_id,
            EmployeeForm.status == "submitted",   # waiting on HR specifically
        )
        .order_by(EmployeeForm.submitted_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())