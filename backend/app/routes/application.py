"""
router.py — FastAPI APIRouter for Applications, Status History, and Tasks.

Mount in main.py:
    from app.api.applications.router import router as applications_router
    app.include_router(applications_router, prefix="/api/v1", tags=["Applications"])
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Project imports  (adjust paths to match your project layout)
# ---------------------------------------------------------------------------
from app.core.database import get_db                        # your AsyncSession dep
from app.core.dependencies import get_current_user   # your auth dep → UUID
from app.schemas.employee.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatus,
    ApplicationStatusUpdate,
    ApplicationUpdate,
    StatusHistoryCreate,
    StatusHistoryResponse,
    TaskCompleteRequest,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.employee.application_services import (
    complete_task,
    create_application,
    create_status_history,
    create_task,
    delete_application,
    delete_task,
    get_application,
    list_applications,
    list_status_history,
    list_tasks,
    update_application,
    update_application_status,
    update_task,
)

application_router = APIRouter()


# ===========================================================================
#  APPLICATIONS  —  CRUD
#  Base path: /applications
# ===========================================================================


@application_router.post(
    "/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new application",
    description=(
        "Creates a new visa application in **draft** status. "
        "Triggered by the 'New Application' button on the My-Applications screen."
    ),
)
async def api_create_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> ApplicationResponse:
    return await create_application(db, payload, current_user_id.user_id)


@application_router.get(
    "/applications",
    response_model=ApplicationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List my applications with KPI summary",
    description=(
        "Returns the KPI cards (Total / In-Progress / Action-Needed / Approved) "
        "and a paginated grid of application cards — the My-Applications screen."
    ),
)
async def api_list_applications(
    status_filter: Optional[ApplicationStatus] = Query(
        None, alias="status", description="Filter by application status"
    ),
    visa_type_id: Optional[uuid.UUID] = Query(
        None, description="Filter by visa type UUID"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> ApplicationListResponse:
    return await list_applications(
        db, current_user_id.user_id, status_filter, visa_type_id, limit, offset
    )


@application_router.get(
    "/applications/{application_id}",
        response_model=ApplicationResponse,
        status_code=status.HTTP_200_OK,
        summary="Get a single application by ID",
    )
async def api_get_application(
        application_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        current_user_id: uuid.UUID = Depends(get_current_user),
    ) -> ApplicationResponse:
        return await get_application(db, application_id, current_user_id.user_id)


@application_router.patch(
    "/applications/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update an application",
    description="Update any combination of editable fields. Only provided fields are written.",
)
async def api_update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> ApplicationResponse:
    return await update_application(db, application_id, payload, current_user_id.user_id)


@application_router.patch(
    "/applications/{application_id}/status",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Change application status (creates history record)",
    description=(
        "Dedicated status-change endpoint. "
        "Automatically appends an immutable row to `application_status_history`."
    ),
)
async def api_update_application_status(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> ApplicationResponse:
    return await update_application_status(
        db,
        application_id,
        payload.status,
        payload.current_stage,
        payload.note,
        current_user_id,
    )


@application_router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a draft application",
    description="Hard-deletes the application. Only **draft** applications can be deleted.",
)
async def api_delete_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> dict:
    return await delete_application(db, application_id, current_user_id.user_id)


# ===========================================================================
#  STATUS HISTORY
#  Base path: /applications/{application_id}/status-history
# ===========================================================================

application_history_router = APIRouter() 
@application_history_router.get(
    "/applications/{application_id}/status-history",
    response_model=List[StatusHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get full status history timeline",
    description="Returns the immutable audit log / 4-stage timeline (Screen 15).",
)
async def api_list_status_history(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> List[StatusHistoryResponse]:
    return await list_status_history(db, application_id)


@application_history_router.post(
    "/applications/{application_id}/status-history",
    response_model=StatusHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually append a status history record",
    description="For attorney/HR to add notes to the timeline without changing the live status.",
)
async def api_create_status_history(
    application_id: uuid.UUID,
    payload: StatusHistoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> StatusHistoryResponse:
    return await create_status_history(db, application_id, payload, current_user_id.user_id)


# ===========================================================================
#  TASKS  (checklist)
#  Base path: /applications/{application_id}/tasks
# ===========================================================================
application_task_router = APIRouter()

@application_task_router.get(
    "/applications/{application_id}/tasks",
    response_model=List[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List all tasks for an application",
    description="Returns the checklist sorted by `sort_order`.",
)
async def api_list_tasks(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> List[TaskResponse]:
    return await list_tasks(db, application_id)


@application_task_router.post(
    "/applications/{application_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a checklist task to an application",
)
async def api_create_task(
    application_id: uuid.UUID,
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> TaskResponse:
    return await create_task(db, application_id, payload, current_user_id.user_id)


@application_task_router.patch(
    "/applications/{application_id}/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update task metadata",
    description="Updates name / description / sort_order. For completion state use `/complete`.",
)
async def api_update_task(
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> TaskResponse:
    return await update_task(db, application_id, task_id, payload, current_user_id.user_id)


@application_task_router.patch(
    "/applications/{application_id}/tasks/{task_id}/complete",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a task complete or incomplete",
    description=(
        "Sets `is_completed`, records `completed_at` timestamp and `completed_by` user. "
        "Send `{\"is_completed\": false}` to undo."
    ),
)
async def api_complete_task(
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> TaskResponse:
    return await complete_task(db, application_id, task_id, payload, current_user_id.user_id)


@application_task_router.delete(
    "/applications/{application_id}/tasks/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a task",
)
async def api_delete_task(
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> dict:
    return await delete_task(db, application_id, task_id, current_user_id.user_id)