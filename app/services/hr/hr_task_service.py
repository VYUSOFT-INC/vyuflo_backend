"""
Task service for HR-facing case management.

HR can:
  - List tasks on any case assigned to them
  - Mark tasks complete / incomplete (on behalf of employee)
  - Add custom tasks to a case
  - Update task metadata
  - Delete custom (non-required) tasks

Uses the same ApplicationTask model as the employee flow.
Separate schemas so HR responses can include extra fields
(e.g. who_should_complete, visibility to employee).

Why this is separate from application_services.py:
  application_services.py uses `app.user_id == current_user_id` for access control —
  which means only the employee can call those task endpoints.

  HR owns cases via `assigned_hr_id == hr_user_id`. This service:
    1. Verifies HR owns the case (via _assert_hr_owns_case)
    2. Then performs the same task CRUD as application_service
    3. Returns HRTaskResponse (same shape as TaskResponse, different priority field)

The underlying ApplicationTask model and DB table are shared.

Relay state machine (for attorney-initiated intake tasks, target="employee"):
  Lawyer creates a task ("intake ask") -> origin="attorney", relay_status="pending_hr_intake"
    -> HR reviews & assigns to employee -> relay_status="assigned_to_employee"
    -> employee completes it -> relay_status auto-advances to "pending_hr_relay"
    -> HR explicitly relays -> relay_status="sent_to_lawyer" (only now does the lawyer see it)

  Existing HR-created tasks (origin="hr", e.g. "Request Document from Attorney")
  keep relay_status="sent_to_lawyer" from creation — fully unaffected, no new gate.

NEW — target="hr" tasks (attorney asks HR directly, no employee involved):
  assigned_to is "hr" from creation, relay_status is never gated on.
  hr_complete_task() below (the same one used for everything else) is all
  that's needed to mark these done — no new endpoint required. HR sees
  them via the ordinary hr_list_tasks() below; the frontend groups them
  separately from the pending_hr_intake queue since they need no
  "Assign to Employee" step at all.

FIXED (dedup): this file previously defined its OWN local copies of
_pack_description / _unpack_description / _advance_relay_on_completion,
identical in logic to app/services/employee/task_relay.py but a second,
separate copy. Both files now import the SAME three functions from the
shared module; only the local names (`_pack_description` etc.) are kept
via aliasing so no call site elsewhere in this file needed to change.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.services.employee.services import db_create, db_delete, db_get_by_id, db_update
from app.models.visamodels import Application, ApplicationTask
from app.schemas.hr.hr_task_schemas import (
    HRTaskCreate,
    HRTaskUpdate,
    HRTaskCompleteRequest,
    HRTaskResponse,
)

# ── Shared HR-relay state machine — single source of truth, also imported
#    by app/services/employee/application_services.py. Aliased to the
#    original local names so every call site below is unchanged.
from app.services.employee.task_relay import (
    pack_task_description as _pack_description,
    unpack_task_description as _unpack_description,
    advance_relay_on_completion as _advance_relay_on_completion,
)


# =============================================================================
# HELPERS
# =============================================================================

async def _assert_hr_owns_case(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> Application:
    """
    Re-declared here to avoid circular imports with hr_case_service.
    Verifies HR is the assigned HR on this case.
    """
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app = result.scalars().first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {application_id} not found.",
        )
    if app.assigned_hr_id != hr_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this case.",
        )
    return app


async def _assert_task_belongs_to_case(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
) -> ApplicationTask:
    task = await db_get_by_id(db, ApplicationTask, task_id)
    if not task or task.application_id != application_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found for case {application_id}.",
        )
    return task


def _build_response(task: ApplicationTask) -> HRTaskResponse:
    """Build HRTaskResponse, decoding all packed fields from description JSON."""
    doc = getattr(task, "document", None)
    priority, plain_desc, due_date, assigned_to, relay_status, origin, target = _unpack_description(task.description)
    return HRTaskResponse(
        id             = task.id,
        application_id = task.application_id,
        task_name      = task.task_name,
        description    = plain_desc or None,
        is_required    = task.is_required,
        is_completed   = task.is_completed,
        sort_order     = task.sort_order,
        priority       = priority,
        due_date       = due_date,
        assigned_to    = assigned_to,
        relay_status   = relay_status,
        origin         = origin,
        target         = target,
        completed_at   = task.completed_at,
        completed_by   = task.completed_by,
        created_at     = task.created_at,
        updated_at     = task.updated_at,
        document_id          = doc.id                          if doc else None,
        document_name        = doc.file_name                   if doc else None,
        document_size_bytes  = doc.file_size_kb * 1024         if doc and doc.file_size_kb else None,
        document_uploaded_at = doc.created_at                  if doc else None,
        document_status      = doc.status                      if doc else None,
        document_rejection_reason = doc.rejection_reason       if doc else None,
        document_version          = doc.version                if doc else None,
    )


# =============================================================================
# LIST TASKS
# =============================================================================

async def hr_list_tasks(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> List[HRTaskResponse]:
    """
    GET /hr/cases/:application_id/tasks
    Returns all tasks for a case, ordered by sort_order.
    HR can see tasks auto-created from visa_type.required_documents
    (created by hr_create_case) plus any custom tasks added later — and,
    per the relay/target model, EVERY attorney-origin task regardless of
    stage (pending_hr_intake, target="hr", etc.) — HR is the one party
    that should always see everything on their own case; the gating is
    only ever about what the EMPLOYEE or the ATTORNEY see.
    """
    await _assert_hr_owns_case(db, application_id, hr_user_id)

    result = await db.execute(
        select(ApplicationTask)
        .options(joinedload(ApplicationTask.document))
        .where(ApplicationTask.application_id == application_id)
        .order_by(ApplicationTask.sort_order, ApplicationTask.created_at)
    )
    tasks = result.scalars().all()
    return [_build_response(t) for t in tasks]


# =============================================================================
# CREATE TASK  (HR-initiated — unaffected: origin="hr", relay_status="sent_to_lawyer",
# target="employee" default, though target isn't meaningful for HR-origin tasks)
# =============================================================================

async def hr_create_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    payload: HRTaskCreate,
    hr_user_id: uuid.UUID,
) -> HRTaskResponse:
    """
    POST /hr/cases/:application_id/tasks
    HR adds a custom task to a case (e.g. "Get signed I-9 from employee").
    These are additional tasks on top of the auto-created required_documents tasks.
    """
    await _assert_hr_owns_case(db, application_id, hr_user_id)

    task = ApplicationTask(
        application_id = application_id,
        task_name      = payload.task_name,
        description    = _pack_description(
            payload.priority, payload.description, payload.due_date, payload.assigned_to,
            relay_status="sent_to_lawyer", origin="hr", target="employee",
        ),
        is_required    = payload.is_required,
        is_completed   = False,
        sort_order     = payload.sort_order,
        created_by     = hr_user_id,
    )
    task = await db_create(db, task)
    return _build_response(task)


# =============================================================================
# UPDATE TASK METADATA
# =============================================================================

async def hr_update_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: HRTaskUpdate,
    hr_user_id: uuid.UUID,
) -> HRTaskResponse:
    """
    PATCH /hr/cases/:application_id/tasks/:task_id
    Updates task name, description, priority, due_date, sort_order, is_required.
    Does NOT change is_completed — use hr_complete_task for that.
    """
    await _assert_hr_owns_case(db, application_id, hr_user_id)
    task = await _assert_task_belongs_to_case(db, application_id, task_id)

    update_data: dict = {"modified_by": hr_user_id}

    if payload.task_name is not None:
        update_data["task_name"] = payload.task_name

    # Re-pack description if priority, text, due_date, or assigned_to changed
    if payload.description is not None or payload.priority is not None or payload.due_date is not None or payload.assigned_to is not None:
        current_priority, current_text, current_due_date, current_assigned_to, current_relay, current_origin, current_target = _unpack_description(task.description)
        new_priority = payload.priority    or current_priority
        new_text     = payload.description if payload.description is not None else current_text
        new_due_date = payload.due_date    if payload.due_date is not None else current_due_date
        new_assigned_to = payload.assigned_to or current_assigned_to
        # relay_status/origin/target are NEVER touched by this general-purpose
        # update — they only move via the dedicated relay endpoints below.
        update_data["description"] = _pack_description(
            new_priority, new_text, new_due_date, new_assigned_to,
            relay_status=current_relay, origin=current_origin, target=current_target,
        )

    if payload.is_required is not None:
        update_data["is_required"] = payload.is_required
    if payload.sort_order is not None:
        update_data["sort_order"] = payload.sort_order

    if len(update_data) == 1:  # only modified_by
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update.",
        )

    await db_update(db, ApplicationTask, task_id, update_data)

    # Reload with document relationship
    result = await db.execute(
        select(ApplicationTask)
        .options(joinedload(ApplicationTask.document))
        .where(ApplicationTask.id == task_id)
    )
    updated = result.scalars().first()
    return _build_response(updated)


# =============================================================================
# COMPLETE / UNCOMPLETE TASK — advances relay_status when applicable
# =============================================================================

async def hr_complete_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: HRTaskCompleteRequest,
    hr_user_id: uuid.UUID,
) -> HRTaskResponse:
    """
    PATCH /hr/cases/:application_id/tasks/:task_id/complete

    HR marks a task complete on behalf of the employee (or their own HR tasks) —
    and this is ALSO how HR completes a target="hr" attorney-direct-request
    task: no separate endpoint needed. advance_relay_on_completion() is a
    no-op for target="hr" tasks (their relay_status never reaches
    "assigned_to_employee"), so this just flips is_completed for them,
    exactly like completing any ordinary task.

    When completing: records completed_at, completed_by, and optional document_id.
    When uncompleting (is_completed=false): clears all completion fields.
    """
    await _assert_hr_owns_case(db, application_id, hr_user_id)
    task = await _assert_task_belongs_to_case(db, application_id, task_id)

    priority, text, due_date, assigned_to, relay_status, origin, target = _unpack_description(task.description)
    new_relay_status = _advance_relay_on_completion(relay_status, origin, payload.is_completed)

    update_data: dict = {
        "is_completed": payload.is_completed,
        "modified_by":  hr_user_id,
    }
    if new_relay_status != relay_status:
        update_data["description"] = _pack_description(
            priority, text, due_date, assigned_to,
            relay_status=new_relay_status, origin=origin, target=target,
        )

    if payload.is_completed:
        update_data["completed_at"] = datetime.now(timezone.utc)
        update_data["completed_by"] = hr_user_id
        if payload.document_id:
            update_data["document_id"] = payload.document_id
    else:
        # Uncomplete — clear all completion state
        update_data["completed_at"] = None
        update_data["completed_by"] = None
        update_data["document_id"]  = None

    await db_update(db, ApplicationTask, task_id, update_data)

    # Reload with document relationship
    result = await db.execute(
        select(ApplicationTask)
        .options(joinedload(ApplicationTask.document))
        .where(ApplicationTask.id == task_id)
    )
    updated = result.scalars().first()
    return _build_response(updated)


# =============================================================================
# HR assigns a lawyer-created intake task to the employee
# =============================================================================

async def hr_assign_intake_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> HRTaskResponse:
    """
    PATCH /hr/cases/{application_id}/tasks/{task_id}/assign-intake

    HR reviews a task the ATTORNEY created with target="employee"
    (relay_status="pending_hr_intake") and pushes it to the employee.
    Only valid on attorney-origin, target="employee" tasks still sitting
    at that exact stage — this is a deliberate HR checkpoint, not a
    rubber stamp: HR is the one who decides the employee should see it.

    target="hr" tasks never reach this function at all — they're
    assigned_to="hr" from creation and HR completes them directly via
    hr_complete_task() above, with no "assign to employee" step.
    """
    await _assert_hr_owns_case(db, application_id, hr_user_id)
    task = await _assert_task_belongs_to_case(db, application_id, task_id)

    priority, text, due_date, assigned_to, relay_status, origin, target = _unpack_description(task.description)
    if origin != "attorney" or relay_status != "pending_hr_intake":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task is not awaiting HR intake review (origin={origin}, relay_status={relay_status}).",
        )

    await db_update(db, ApplicationTask, task_id, {
        "description": _pack_description(
            priority, text, due_date, "employee",
            relay_status="assigned_to_employee", origin=origin, target=target,
        ),
        "modified_by": hr_user_id,
    })

    result = await db.execute(
        select(ApplicationTask)
        .options(joinedload(ApplicationTask.document))
        .where(ApplicationTask.id == task_id)
    )
    return _build_response(result.scalars().first())


# =============================================================================
# HR relays a completed attorney-origin task back to the lawyer
# =============================================================================

async def hr_relay_task_to_attorney(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> HRTaskResponse:
    """
    PATCH /hr/cases/{application_id}/tasks/{task_id}/relay-to-lawyer

    Mirrors hr_assign_document_to_attorney() in hr_approval_service.py —
    same "HR is the explicit final step" pattern, now for tasks. Only valid
    once the employee has completed the task and it's sitting in
    "pending_hr_relay" (see advance_relay_on_completion in task_relay.py).

    Not applicable to target="hr" tasks — they never enter "pending_hr_relay"
    since there's no employee step for them at all.
    """
    await _assert_hr_owns_case(db, application_id, hr_user_id)
    task = await _assert_task_belongs_to_case(db, application_id, task_id)

    priority, text, due_date, assigned_to, relay_status, origin, target = _unpack_description(task.description)
    if origin != "attorney" or relay_status != "pending_hr_relay":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task is not awaiting relay to the lawyer (origin={origin}, relay_status={relay_status}, completed={task.is_completed}).",
        )

    await db_update(db, ApplicationTask, task_id, {
        "description": _pack_description(
            priority, text, due_date, assigned_to,
            relay_status="sent_to_lawyer", origin=origin, target=target,
        ),
        "modified_by": hr_user_id,
    })

    result = await db.execute(
        select(ApplicationTask)
        .options(joinedload(ApplicationTask.document))
        .where(ApplicationTask.id == task_id)
    )
    return _build_response(result.scalars().first())


# =============================================================================
# DELETE TASK
# =============================================================================

async def hr_delete_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> dict:
    """
    DELETE /hr/cases/:application_id/tasks/:task_id

    HR can only delete tasks they created (is_required=False custom tasks).
    Required tasks auto-created from visa_type.required_documents cannot be deleted
    — they represent actual document requirements.
    """
    await _assert_hr_owns_case(db, application_id, hr_user_id)
    task = await _assert_task_belongs_to_case(db, application_id, task_id)

    if task.is_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Required tasks cannot be deleted. "
                "They represent document requirements for this visa type. "
                "Mark them complete instead."
            ),
        )

    deleted = await db_delete(db, ApplicationTask, task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )
    return {"detail": "Task deleted successfully."}