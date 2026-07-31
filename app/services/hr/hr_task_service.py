# app/services/hr/hr_task_service.py
"""
Task service for HR-facing case management.

Why this is separate from application_service.py:
  application_service.py uses `app.user_id == current_user_id` for access control —
  which means only the employee can call those task endpoints.

  HR owns cases via `assigned_hr_id == hr_user_id`. This service:
    1. Verifies HR owns the case (via _assert_hr_owns_case)
    2. Then performs the same task CRUD as application_service
    3. Returns HRTaskResponse (same shape as TaskResponse, different priority field)

The underlying ApplicationTask model and DB table are shared.
"""
from __future__ import annotations

import json
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


def _parse_priority(description: str | None) -> str:
    """
    Priority is stored as a JSON prefix in description:
      {"priority": "critical", "text": "Upload I-129 Form"}
    Falls back to "medium" for legacy plain-text descriptions.
    """
    if not description:
        return "medium"
    try:
        if description.startswith("{"):
            data = json.loads(description)
            return data.get("priority", "medium")
    except (json.JSONDecodeError, TypeError):
        pass
    return "medium"


def _pack_description(priority: str, text: str | None) -> str:
    """Store priority in description JSON so we don't need a new column."""
    return json.dumps({"priority": priority, "text": text or ""}, ensure_ascii=False)


def _unpack_description(raw: str | None) -> tuple[str, str]:
    """Returns (priority, plain_text_description)."""
    if not raw:
        return "medium", ""
    try:
        if raw.startswith("{"):
            data = json.loads(raw)
            return data.get("priority", "medium"), data.get("text", "")
    except (json.JSONDecodeError, TypeError):
        pass
    return "medium", raw  # legacy plain text


def _build_response(task: ApplicationTask) -> HRTaskResponse:
    """Build HRTaskResponse, decoding priority from description JSON."""
    doc = getattr(task, "document", None)
    priority, plain_desc = _unpack_description(task.description)
    return HRTaskResponse(
        id             = task.id,
        application_id = task.application_id,
        task_name      = task.task_name,
        description    = plain_desc or None,
        is_required    = task.is_required,
        is_completed   = task.is_completed,
        sort_order     = task.sort_order,
        priority       = priority,
        completed_at   = task.completed_at,
        completed_by   = task.completed_by,
        created_at     = task.created_at,
        updated_at     = task.updated_at,
        document_id          = doc.id                          if doc else None,
        document_name        = doc.file_name                   if doc else None,
        document_size_bytes  = doc.file_size_kb * 1024         if doc and doc.file_size_kb else None,
        document_uploaded_at = doc.created_at                  if doc else None,
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
    (created by hr_create_case) plus any custom tasks added later.
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
# CREATE TASK
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
        description    = _pack_description(payload.priority, payload.description),
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
    Updates task name, description, priority, sort_order, is_required.
    Does NOT change is_completed — use hr_complete_task for that.
    """
    await _assert_hr_owns_case(db, application_id, hr_user_id)
    task = await _assert_task_belongs_to_case(db, application_id, task_id)

    update_data: dict = {"modified_by": hr_user_id}

    if payload.task_name is not None:
        update_data["task_name"] = payload.task_name

    # Re-pack description if priority or text changed
    if payload.description is not None or payload.priority is not None:
        current_priority, current_text = _unpack_description(task.description)
        new_priority = payload.priority    or current_priority
        new_text     = payload.description if payload.description is not None else current_text
        update_data["description"] = _pack_description(new_priority, new_text)

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
# COMPLETE / UNCOMPLETE TASK
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

    HR marks a task complete on behalf of the employee (or their own HR tasks).
    This is what the Action Items checkboxes in HRCaseDetail call.

    When completing: records completed_at, completed_by, and optional document_id.
    When uncompleting (is_completed=false): clears all completion fields.
    """
    await _assert_hr_owns_case(db, application_id, hr_user_id)
    await _assert_task_belongs_to_case(db, application_id, task_id)

    update_data: dict = {
        "is_completed": payload.is_completed,
        "modified_by":  hr_user_id,
    }

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