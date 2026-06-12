"""
application_service.py — Service layer for Applications, Status History, and Tasks.

Every public function:
  • Accepts an AsyncSession + validated Pydantic schema / raw params
  • Delegates DB I/O to the shared db_* helpers
  • Raises HTTPException with explicit status codes on errors
  • Returns Pydantic response schemas (or raw ORM objects where the router
    calls model_validate itself)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

# ---------------------------------------------------------------------------
# Project imports  (adjust paths to match your project layout)
# ---------------------------------------------------------------------------
from app.services.services import (
    db_create,
    db_delete,
    db_get_by_field,
    db_get_by_id,
    db_list,
    db_update,
)
from app.models.visamodels import Application, ApplicationStatusHistory, ApplicationTask, VisaType
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatus,
    ApplicationStage,
    ApplicationUpdate,
    StatusHistoryCreate,
    StatusHistoryResponse,
    TaskCompleteRequest,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)


# ===========================================================================
# HELPERS
# ===========================================================================


def _generate_application_number() -> str:
    """
    Generates a unique application reference number, e.g. VF-8924-X.
    Replace with your own sequence logic if needed.
    """
    suffix = uuid.uuid4().hex[:4].upper()
    number = uuid.uuid4().int % 90000 + 10000
    return f"VF-{number}-{suffix[0]}"


async def _assert_application_exists(
    db: AsyncSession, application_id: uuid.UUID
) -> Application:
    app = await db_get_by_id(db, Application, application_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found.",
        )
    return app


async def _assert_task_exists(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
) -> ApplicationTask:
    task = await db_get_by_id(db, ApplicationTask, task_id)
    if not task or task.application_id != application_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found for application {application_id}.",
        )
    return task


# ===========================================================================
# APPLICATION SERVICE
# ===========================================================================


STAGE_PROGRESS: dict[str, int] = {
    "profile_eligibility": 25,
    "documentation":       50,
    "lca_filing":          75,
    "uscis_submission":    90,
}
 
 
# =============================================================================
# FULL FIXED FUNCTION — replaces create_application in application_service.py
# =============================================================================
 
async def create_application(
    db: AsyncSession,
    payload: ApplicationCreate,
    current_user_id: uuid.UUID,
) -> ApplicationResponse:
    """
    POST /applications
    Creates a new application, immediately activates it to
    'profile_eligibility' stage, and auto-creates tasks from
    visa_type.required_documents.
    """
 
    # ── 1. Generate unique application number ─────────────────────────────────
    app_number = _generate_application_number()
    existing   = await db_get_by_field(db, Application, "application_number", app_number)
    if existing:
        app_number = _generate_application_number()  # retry once on collision
 
    # ── 2. Block duplicate drafts for same user + visa type ───────────────────
    duplicate = await db.execute(
        select(Application).where(
            Application.user_id      == current_user_id,
            Application.visa_type_id == payload.visa_type_id,
            Application.status       == "draft",
        )
    )
    if duplicate.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "You already have a draft application for this visa type. "
                "Please complete or delete it before creating a new one."
            ),
        )
 
    # ── 3. Create the application row ─────────────────────────────────────────
    new_app = Application(
        application_number   = app_number,
        user_id              = current_user_id,
        visa_type_id         = payload.visa_type_id,
        sponsor_employer     = payload.sponsor_employer,
        status               = "draft",        # will be updated below
        current_stage        = None,            # will be updated below
        progress_percent     = 0,              # will be updated below
        start_date           = payload.start_date,
        due_date             = payload.due_date,
        is_draft             = True,           # will be updated below
        has_action_required  = False,
        assigned_attorney_id = payload.assigned_attorney_id,
        assigned_hr_id       = payload.assigned_hr_id,
        notes                = payload.notes,
        created_by           = current_user_id,
    )
    new_app = await db_create(db, new_app)
 
    # ── 4. Immediately activate — set stage, status, progress, start_date ─────
    #       This is what makes the frontend timeline + progress bar work
    #       on the very first load of ApplicationDetail.
    await db_update(db, Application, new_app.id, {
        "current_stage":    "profile_eligibility",
        "status":           "in_progress",
        "progress_percent": STAGE_PROGRESS["profile_eligibility"],  # 25
        "start_date":       datetime.now(timezone.utc).date(),
        "is_draft":         False,
        "modified_by":      current_user_id,
    })
 
    # ── 5. Write first history row ────────────────────────────────────────────
    #       Gives the timeline "Completed on <date>" for Profile & Eligibility
    history = ApplicationStatusHistory(
        application_id = new_app.id,
        stage          = "profile_eligibility",
        status         = "in_progress",
        note           = "Profile & Eligibility completed on application creation",
        completed_at   = datetime.now(timezone.utc),
        changed_by     = current_user_id,
        created_by     = current_user_id,
    )
    await db_create(db, history)
 
    # ── 6. Auto-create tasks from visa_type.required_documents ───────────────
    #       The seed data defines required_documents as a JSON list per visa type.
    #       e.g. H-1B → ["Passport Copy", "Educational Transcripts", ...]
    visa_type = await db_get_by_id(db, VisaType, payload.visa_type_id)
    if not visa_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visa type {payload.visa_type_id} not found.",
        )
 
    docs = visa_type.required_documents
    # required_documents may be stored as a JSON string in the DB
    if isinstance(docs, str):
        import json
        docs = json.loads(docs)
 
    for index, doc_name in enumerate(docs or []):
        task = ApplicationTask(
            application_id = new_app.id,
            task_name      = doc_name,
            description    = f"Upload {doc_name} for {visa_type.code} application",
            is_required    = True,
            is_completed   = False,
            sort_order     = index + 1,
            created_by     = current_user_id,
        )
        await db_create(db, task)
 
    # ── 7. Reload with visa_type relationship and return ──────────────────────
    result = await db.execute(
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(Application.id == new_app.id)
    )
    refreshed = result.scalars().first()
    return ApplicationResponse.model_validate(refreshed)
 
 
# async def create_application(
#     db: AsyncSession,
#     payload: ApplicationCreate,
#     current_user_id: uuid.UUID,
# ) -> ApplicationResponse:
#     """
#     POST /applications
#     Creates a new application in 'draft' status.
#     Auto-creates tasks from visa_type.required_documents.
#     """
#     app_number = _generate_application_number()

#     # Check uniqueness
#     existing = await db_get_by_field(db, Application, "application_number", app_number)
#     if existing:
#         app_number = _generate_application_number()
#     # ── Block duplicate drafts for same user + visa type ──────────────────
#     existing = await db.execute(
#         select(Application).where(
#             Application.user_id      == current_user_id,
#             Application.visa_type_id == payload.visa_type_id,
#             Application.status       == "draft",
#         )
#     )
#     if existing.scalars().first():
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="You already have a draft application for this visa type. "
#                    "Please complete or delete it before creating a new one.",
#         )
#     new_app = Application(
#         application_number   = app_number,
#         user_id              = current_user_id,
#         visa_type_id         = payload.visa_type_id,
#         sponsor_employer     = payload.sponsor_employer,
#         status               = "draft",
#         current_stage        = None,
#         progress_percent     = 0,
#         start_date           = payload.start_date,
#         due_date             = payload.due_date,
#         is_draft             = payload.is_draft,    
#         has_action_required  = False,
#         assigned_attorney_id = payload.assigned_attorney_id,
#         assigned_hr_id       = payload.assigned_hr_id,
#         notes                = payload.notes,
#         created_by           = current_user_id,
#     )
#     new_app = await db_create(db, new_app)

#     # ── Auto-create tasks from visa_type.required_documents ──────────────────
#     visa_type = await db_get_by_id(db, VisaType, payload.visa_type_id)
#     visa_type = await db_get_by_id(db, VisaType, payload.visa_type_id)
#     docs = visa_type.required_documents
#     if isinstance(docs, str):
#         import json
#         docs = json.loads(docs)

#     for index, doc_name in enumerate(docs):
#         task = ApplicationTask(
#             application_id = new_app.id,
#             task_name      = doc_name,
#             description    = f"Upload {doc_name} for {visa_type.code} application",
#             is_required    = True,
#             is_completed   = False,
#             sort_order     = index + 1,
#             created_by     = current_user_id,
#         )
#         await db_create(db, task)

#     return ApplicationResponse.model_validate(new_app)


async def get_application(
    db: AsyncSession,
    application_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> ApplicationResponse:
    result = await db.execute(
        select(Application)
        .options(joinedload(Application.visa_type))    # ← proper joinedload
        .where(Application.id == application_id)
    )
    app = result.scalars().first()
    if not app:
        raise HTTPException(status_code=404, detail=f"Application {application_id} not found.")
    if app.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this application.")
    return ApplicationResponse.model_validate(app)

from sqlalchemy.orm import joinedload

async def list_applications(
    db: AsyncSession,
    current_user_id: uuid.UUID,
    status_filter: Optional[ApplicationStatus] = None,
    visa_type_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> ApplicationListResponse:
    """
    GET /applications
    Returns KPI summary (total / in_progress / action_needed / approved)
    + paginated application cards with visa_type nested object.
    """

    # ── 1. Filtered items — with visa_type eagerly loaded ─────────────────────
    stmt = (
        select(Application)
        .options(joinedload(Application.visa_type))   # ← loads visa_type in 1 query
        .where(Application.user_id == current_user_id)
    )
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)
    if visa_type_id:
        stmt = stmt.where(Application.visa_type_id == visa_type_id)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()

    # ── 2. KPI counts — all apps, no filters, visa_type loaded too ────────────
    kpi_stmt = (
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(Application.user_id == current_user_id)
    )
    kpi_result = await db.execute(kpi_stmt)
    all_apps = kpi_result.scalars().all()

    total         = len(all_apps)
    in_progress   = sum(1 for a in all_apps if a.status == "in_progress")
    action_needed = sum(1 for a in all_apps if a.status == "action_needed")
    approved      = sum(1 for a in all_apps if a.status == "approved")

    # ── 3. Build response ─────────────────────────────────────────────────────
    return ApplicationListResponse(
        total         = total,
        in_progress   = in_progress,
        action_needed = action_needed,
        approved      = approved,
        items         = [ApplicationResponse.model_validate(a) for a in items],
    )

async def update_application(
    db: AsyncSession,
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    current_user_id: uuid.UUID,
) -> ApplicationResponse:
    """
    PATCH /applications/{application_id}
    Partial update.  Only provided (non-None) fields are written.
    """
    app = await _assert_application_exists(db, application_id)

    if app.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this application.",
        )

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update.",
        )

    update_data["modified_by"] = current_user_id
    updated = await db_update(db, Application, application_id, update_data)
    return ApplicationResponse.model_validate(updated)


async def update_application_status(
    db: AsyncSession,
    application_id: uuid.UUID,
    new_status: ApplicationStatus,
    new_stage: Optional[ApplicationStage],
    note: Optional[str],
    current_user_id: uuid.UUID,
) -> ApplicationResponse:
    """
    PATCH /applications/{application_id}/status
    Changes status AND writes an immutable history record.
    """
    app = await _assert_application_exists(db, application_id)

    update_data: dict = {
        "status": new_status,
        "modified_by": current_user_id,
    }
    if new_stage is not None:
        update_data["current_stage"] = new_stage
    if new_status == "action_needed":
        update_data["has_action_required"] = True
        update_data["action_required_note"] = note
    if new_status == "submitted":
        update_data["submission_date"] = datetime.now(timezone.utc)
        update_data["is_draft"] = False
    if new_status in ("approved", "rejected", "withdrawn"):
        update_data["has_action_required"] = False

    await db_update(db, Application, application_id, update_data)

    # Write immutable history row
    history = ApplicationStatusHistory(
        application_id=application_id,
        stage=new_stage or app.current_stage,
        status=new_status,
        note=note,
        completed_at=datetime.now(timezone.utc) if new_status == "approved" else None,
        changed_by=current_user_id,
        created_by=current_user_id,
    )
    await db_create(db, history)

    refreshed = await db_get_by_id(db, Application, application_id)
    return ApplicationResponse.model_validate(refreshed)


async def delete_application(
    db: AsyncSession,
    application_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> dict:
    """
    DELETE /applications/{application_id}
    Hard delete.  Only allowed on draft applications.
    """
    app = await _assert_application_exists(db, application_id)

    if app.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this application.",
        )
    if app.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft applications can be deleted.",
        )

    deleted = await db_delete(db, Application, application_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )
    return {"detail": "Application deleted successfully."}


# ===========================================================================
# STATUS HISTORY SERVICE
# ===========================================================================


async def list_status_history(
    db: AsyncSession,
    application_id: uuid.UUID,
) -> List[StatusHistoryResponse]:
    """
    GET /applications/{application_id}/status-history
    Timeline view (Screen 15 — 4-stage tracker).
    """
    await _assert_application_exists(db, application_id)
    rows = await db_list(
        db,
        ApplicationStatusHistory,
        filters=[ApplicationStatusHistory.application_id == application_id],
        limit=200,
    )
    return [StatusHistoryResponse.model_validate(r) for r in rows]


async def create_status_history(
    db: AsyncSession,
    application_id: uuid.UUID,
    payload: StatusHistoryCreate,
    current_user_id: uuid.UUID,
) -> StatusHistoryResponse:
    """
    POST /applications/{application_id}/status-history
    Manually append a history record (attorney / HR notes).
    """
    await _assert_application_exists(db, application_id)

    history = ApplicationStatusHistory(
        application_id=application_id,
        stage=payload.stage,
        status=payload.status,
        note=payload.note,
        completed_at=payload.completed_at,
        changed_by=current_user_id,
        created_by=current_user_id,
    )
    history = await db_create(db, history)
    return StatusHistoryResponse.model_validate(history)


# ===========================================================================
# TASK SERVICE
# ===========================================================================


async def list_tasks(
    db: AsyncSession,
    application_id: uuid.UUID,
) -> List[TaskResponse]:
    await _assert_application_exists(db, application_id)

    result = await db.execute(
        select(ApplicationTask)
        .options(joinedload(ApplicationTask.document))   # ← loads document in 1 query
        .where(ApplicationTask.application_id == application_id)
        .order_by(ApplicationTask.sort_order)
    )
    tasks = result.scalars().all()
    return [_build_task_response(t) for t in tasks]

async def create_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    payload: TaskCreate,
    current_user_id: uuid.UUID,
) -> TaskResponse:
    """
    POST /applications/{application_id}/tasks
    Adds a checklist item to the application.
    """
    await _assert_application_exists(db, application_id)

    task = ApplicationTask(
        application_id=application_id,
        task_name=payload.task_name,
        description=payload.description,
        is_required=payload.is_required,
        sort_order=payload.sort_order,
        created_by=current_user_id,
    )
    task = await db_create(db, task)
    return TaskResponse.model_validate(task)


async def update_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskUpdate,
    current_user_id: uuid.UUID,
) -> TaskResponse:
    """
    PATCH /applications/{application_id}/tasks/{task_id}
    Updates task metadata (not completion state — use complete_task for that).
    """
    await _assert_task_exists(db, application_id, task_id)

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update.",
        )
    update_data["modified_by"] = current_user_id

    updated = await db_update(db, ApplicationTask, task_id, update_data)
    return TaskResponse.model_validate(updated)


# REPLACE complete_task — link document_id when completing
async def complete_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskCompleteRequest,
    current_user_id: uuid.UUID,
) -> TaskResponse:
    await _assert_task_exists(db, application_id, task_id)

    update_data: dict = {
        "is_completed": payload.is_completed,
        "modified_by":  current_user_id,
    }
    if payload.is_completed:
        update_data["completed_at"] = datetime.now(timezone.utc)
        update_data["completed_by"] = current_user_id
        if payload.document_id:                          # ← ADD
            update_data["document_id"] = payload.document_id
    else:
        update_data["completed_at"] = None
        update_data["completed_by"] = None
        update_data["document_id"]  = None               # ← ADD clear on undo

    await db_update(db, ApplicationTask, task_id, update_data)

    # Reload with document relationship
    result = await db.execute(
        select(ApplicationTask)
        .options(joinedload(ApplicationTask.document))
        .where(ApplicationTask.id == task_id)
    )
    updated = result.scalars().first()
    return _build_task_response(updated)


# ADD this helper function — builds TaskResponse with document fields
def _build_task_response(task: ApplicationTask) -> TaskResponse:
    doc = getattr(task, "document", None)
    return TaskResponse(
        id             = task.id,
        application_id = task.application_id,
        task_name      = task.task_name,
        description    = task.description,
        is_required    = task.is_required,
        is_completed   = task.is_completed,
        sort_order     = task.sort_order,
        completed_at   = task.completed_at,
        completed_by   = task.completed_by,
        created_at     = task.created_at,
        updated_at     = task.updated_at,
        # document fields — only when document is linked
        document_id          = doc.id                      if doc else None,
        document_name        = doc.file_name               if doc else None,
        document_size_bytes  = doc.file_size_kb * 1024     if doc and doc.file_size_kb else None,
        document_uploaded_at = doc.created_at              if doc else None,
    )


async def delete_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> dict:
    """
    DELETE /applications/{application_id}/tasks/{task_id}
    """
    await _assert_task_exists(db, application_id, task_id)

    deleted = await db_delete(db, ApplicationTask, task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )
    return {"detail": "Task deleted successfully."}