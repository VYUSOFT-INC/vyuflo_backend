# app/routes/hr_task_routes.py
"""
FastAPI router for HR task management on cases.

Mount in main.py ALONGSIDE hr_case_router:
    from app.routes.hr_task_routes import hr_task_router
    app.include_router(hr_task_router, prefix="/api/v1/hr", tags=["HR Tasks"])

Resulting endpoints:
    GET    /api/v1/hr/cases/{application_id}/tasks
    POST   /api/v1/hr/cases/{application_id}/tasks
    PATCH  /api/v1/hr/cases/{application_id}/tasks/{task_id}
    PATCH  /api/v1/hr/cases/{application_id}/tasks/{task_id}/complete
    DELETE /api/v1/hr/cases/{application_id}/tasks/{task_id}

Why separate from hr_case_routes.py:
  Keeps each file focused. hr_case_routes owns the case lifecycle;
  hr_task_routes owns the checklist. Both mount at the same prefix.
"""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User
from app.schemas.hr.hr_task_schemas import (
    HRTaskCompleteRequest,
    HRTaskCreate,
    HRTaskResponse,
    HRTaskUpdate,
)
from app.services.hr.hr_task_service import (
    hr_complete_task,
    hr_create_task,
    hr_delete_task,
    hr_list_tasks,
    hr_update_task,
)

hr_task_router = APIRouter()


@hr_task_router.get(
    "/cases/{application_id}/tasks",
    response_model=List[HRTaskResponse],
    status_code=status.HTTP_200_OK,
    summary="HR: List all tasks (action items) for a case",
    description="""
Returns all `application_tasks` for this case, ordered by `sort_order`.

Includes tasks auto-created from `visa_type.required_documents` when HR
created the case, plus any custom tasks HR added afterward.

This is what powers the **Action Items** checklist in `HRCaseDetail`.
    """,
)
async def list_hr_tasks(
    application_id: uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user:   User         = Depends(get_current_user),
) -> List[HRTaskResponse]:
    return await hr_list_tasks(db, application_id, current_user.user_id)


@hr_task_router.post(
    "/cases/{application_id}/tasks",
    response_model=HRTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="HR: Add a custom task to a case",
    description="""
HR adds a custom checklist item beyond the auto-generated required_documents tasks.

Examples:
  - "Get employee to sign I-9 form"
  - "Confirm work location with manager"
  - "Submit LCA to DOL portal"

Priority is stored in the `description` field as a JSON prefix and decoded
on read — no schema migration required.
    """,
)
async def create_hr_task(
    application_id: uuid.UUID,
    payload:        HRTaskCreate,
    db:             AsyncSession = Depends(get_db),
    current_user:   User         = Depends(get_current_user),
) -> HRTaskResponse:
    return await hr_create_task(db, application_id, payload, current_user.user_id)


@hr_task_router.patch(
    "/cases/{application_id}/tasks/{task_id}",
    response_model=HRTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: Update task metadata",
    description="Update task name, description, priority, sort_order. Use `/complete` to change completion state.",
)
async def update_hr_task(
    application_id: uuid.UUID,
    task_id:        uuid.UUID,
    payload:        HRTaskUpdate,
    db:             AsyncSession = Depends(get_db),
    current_user:   User         = Depends(get_current_user),
) -> HRTaskResponse:
    return await hr_update_task(db, application_id, task_id, payload, current_user.user_id)


@hr_task_router.patch(
    "/cases/{application_id}/tasks/{task_id}/complete",
    response_model=HRTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="HR: Mark a task complete or incomplete",
    description="""
Toggles task completion. HR can check off tasks on behalf of the case.

- `{ "is_completed": true }` — marks done, records `completed_at` + `completed_by`
- `{ "is_completed": false }` — undoes completion, clears all completion fields
- `{ "is_completed": true, "document_id": "uuid" }` — marks done AND links uploaded document
    """,
)
async def complete_hr_task(
    application_id: uuid.UUID,
    task_id:        uuid.UUID,
    payload:        HRTaskCompleteRequest,
    db:             AsyncSession = Depends(get_db),
    current_user:   User         = Depends(get_current_user),
) -> HRTaskResponse:
    return await hr_complete_task(db, application_id, task_id, payload, current_user.user_id)


@hr_task_router.delete(
    "/cases/{application_id}/tasks/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="HR: Delete a custom task",
    description="""
Deletes a custom task added by HR. Required tasks (auto-created from
`visa_type.required_documents`) cannot be deleted — they represent actual
document requirements for the visa petition.
    """,
)
async def delete_hr_task(
    application_id: uuid.UUID,
    task_id:        uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user:   User         = Depends(get_current_user),
) -> dict:
    return await hr_delete_task(db, application_id, task_id, current_user.user_id)