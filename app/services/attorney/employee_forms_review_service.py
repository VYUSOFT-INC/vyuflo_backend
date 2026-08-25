"""
employee_forms_review_service.py — attorney actions on submitted employee
forms: request corrections, approve, view version history.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.visamodels import Application, AuditLog, EmployeeForm, EmployeeFormVersion,FormCorrection, Notification
from app.services.employee.services import db_create


async def request_corrections(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
    target: str,              
    fields: list[str],    
    review_note: str,
) -> EmployeeForm:
    form = await _get_form_for_attorney(db, attorney_id, form_type, form_id)

    if form.status != "hr_approved": 
        raise ConflictException("Only an HR-approved form can be sent back for corrections.")

    form.status = "needs_corrections"
    form.review_note = review_note
    form.reviewed_by = attorney_id
    form.reviewed_at = datetime.now(timezone.utc)
    form.last_action_by = attorney_id            
    form.last_action_by_role = "attorney"        
    form.last_action_at = datetime.now(timezone.utc)  
    await db.flush()
    await db.refresh(form)

    await db_create(db, FormCorrection(
        form_type=form_type,
        form_id=form.id,
        target=target,
        fields=fields,
        note=review_note,
        requested_by=attorney_id,
    ))

    app_result = await db.execute(select(Application).where(Application.id == form.application_id))
    application = app_result.scalar_one_or_none()

    # CHANGED — recipient depends on who the correction is targeted at
    if target == "employee":
        recipient_id = form.employee_id
        cta_url = f"/employee/forms/{form_type}/{form.id}"
    else:  # target == "hr"
        recipient_id = application.assigned_hr_id if application else None
        cta_url = f"/hr/forms/{form_type}/{form.id}"

    if recipient_id:
        await db_create(db, Notification(
            user_id=recipient_id,
            notification_type="case_status_updated",
            category="case_update",
            priority="high",
            title=f"{form_type.upper()} needs corrections",
            body=review_note,
            application_id=form.application_id,
            actor_id=attorney_id,
            cta_primary_label="Fix and resubmit",
            cta_primary_url=cta_url,
            created_by=attorney_id,
        ))

    # existing "let HR know too" block only makes sense when target was the employee
    if target == "employee" and application and application.assigned_hr_id:
        await db_create(db, Notification(
            user_id=application.assigned_hr_id,
            notification_type="case_status_updated",
            category="case_update",
            priority="medium",
            title=f"Attorney requested corrections on {form_type.upper()}",
            body=review_note,
            application_id=application.id,
            actor_id=attorney_id,
            created_by=attorney_id,
        ))

    await db_create(db, AuditLog(
        actor_id=attorney_id, actor_type="user", action="employee_form.corrections_requested",
        resource_type="employee_form", resource_id=form.id, description=review_note, severity="info",
    ))
    return form


async def approve_form(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
    review_note: str | None,
) -> EmployeeForm:
    form = await _get_form_for_attorney(db, attorney_id, form_type, form_id)

    if form.status != "hr_approved":  
        raise ConflictException("Only an HR-approved form can be approved.")

    form.status = "approved"
    form.review_note = review_note
    form.reviewed_by = attorney_id
    form.reviewed_at = datetime.now(timezone.utc)
    form.last_action_by = attorney_id            
    form.last_action_by_role = "attorney"        
    form.last_action_at = datetime.now(timezone.utc)  
    await db.flush()
    await db.refresh(form)

    await db_create(db, AuditLog(
        actor_id=attorney_id, actor_type="user", action="employee_form.approved",
        resource_type="employee_form", resource_id=form.id, description=review_note, severity="info",
    ))
    return form

async def mark_form_completed(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
) -> EmployeeForm:
    form = await _get_form_for_attorney(db, attorney_id, form_type, form_id)

    if form.status != "approved":
        raise ConflictException("Form must be approved before it can be marked completed.")

    form.status = "completed"
    await db.flush()
    await db.refresh(form)

    await db_create(db, AuditLog(
        actor_id=attorney_id, actor_type="user", action="employee_form.completed",
        resource_type="employee_form", resource_id=form.id, severity="info",
    ))
    return form


async def list_form_versions(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
) -> list[EmployeeFormVersion]:
    await _get_form_for_attorney(db, attorney_id, form_type, form_id)  # ownership/assignment check

    result = await db.execute(
        select(EmployeeFormVersion)
        .where(EmployeeFormVersion.employee_form_id == form_id)
        .order_by(EmployeeFormVersion.version_number.desc())
    )
    return list(result.scalars().all())

async def list_form_corrections(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
) -> list[FormCorrection]:
    await _get_form_for_attorney(db, attorney_id, form_type, form_id)

    result = await db.execute(
        select(FormCorrection)
        .where(FormCorrection.form_id == form_id, FormCorrection.form_type == form_type)
        .order_by(FormCorrection.created_at.desc())
    )
    return list(result.scalars().all())


async def _get_form_for_attorney(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    form_type: str,
    form_id: uuid.UUID,
) -> EmployeeForm:
    result = await db.execute(
        select(EmployeeForm).where(EmployeeForm.id == form_id, EmployeeForm.form_type == form_type)
    )
    form = result.scalar_one_or_none()
    if not form:
        raise NotFoundException("Form not found")

    app_result = await db.execute(select(Application).where(Application.id == form.application_id))
    application = app_result.scalar_one_or_none()
    if not application or application.assigned_attorney_id != attorney_id:
        raise ForbiddenException("You are not the assigned attorney for this case")

    return form

async def list_attorney_forms(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[EmployeeForm]:
    """All forms across every case assigned to this attorney — the queue screen."""
    query = (
        select(EmployeeForm)
        .join(Application, Application.id == EmployeeForm.application_id)
        .where(Application.assigned_attorney_id == attorney_id)
    )
    if status_filter:
        query = query.where(EmployeeForm.status == status_filter)

    query = query.order_by(EmployeeForm.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())

