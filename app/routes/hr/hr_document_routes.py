# app/routes/hr_document_routes.py
#
# HR-side document endpoints.
# These are the backend counterparts to hrDocumentApi.ts.
# Add to main.py:
#   from app.routes.hr_document_routes import hr_document_router
#   app.include_router(hr_document_router, prefix="/api/v1/hr", tags=["HR Documents"])

import uuid
import os
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import (
    Document, DocumentType, Application, DocumentActivity, ApplicationTask,
)
from app.schemas.attorney.document_request import DocumentRequestCreate, DocumentRequestPriority
from app.schemas.employee.document import DocumentListResponse, DocumentResponse
from app.services.employee import storage
from app.services.employee.document_service import (
    get_document_file_url, upload_document,
)
from app.services.employee.services import db_create, db_update
from app.services.hr.hr_document_request_service import hr_create_document_request
from app.services.employee.notification_service import fire_document_verified, fire_document_rejected


hr_document_router = APIRouter()


def _assert_hr_access(application: Application, hr_user_id: uuid.UUID):
    """HR can only access cases assigned to them."""
    if application.assigned_hr_id != hr_user_id:
        raise HTTPException(status_code=403, detail="Access denied to this case.")


import re


def _normalize_name(s: str) -> str:
    """Lowercase, collapse underscores/hyphens/whitespace to single spaces,
    so "offer_letter" and "Offer Letter" compare equal. Plain ILIKE can't
    do this — SQL doesn't know '_' and ' ' are "the same word.\""""
    return re.sub(r"[\s_\-]+", " ", s or "").strip().lower()


async def _relink_task_to_document(db: AsyncSession, doc: Document, actor_id: uuid.UUID):
    """When HR verifies/rejects a document, make sure the matching task
    actually points at THIS document — not whatever it was linked to
    before (or nothing at all).

    upload_document() only auto-links a new upload to a task when that
    task is still incomplete (only_incomplete=True) and the name roughly
    matches. So a document uploaded after its task was already "done" —
    a second "Passport Copy" HR uploads on top of one the employee already
    submitted, for example — is created successfully but never linked to
    any task at all. HR can find and verify it, but the employee's
    task-driven view has no way to know it exists, since no task points
    to it. Re-linking here, unconditionally (regardless of is_completed),
    is what makes "HR verified 5 documents" actually mean "the employee
    sees 5 documents verified."

    Matching is done in Python on a normalized string (not a raw SQL
    ILIKE) because task_name is stored as human text ("Offer Letter")
    while document_type.name can be an underscored slug ("offer_letter")
    when auto-created during upload — ILIKE treats those as unrelated
    strings and would silently match nothing."""
    if not doc.application_id or not doc.document_type:
        return
    doc_type_norm = _normalize_name(doc.document_type.name)
    if not doc_type_norm:
        return
    tasks_result = await db.execute(
        select(ApplicationTask).where(ApplicationTask.application_id == doc.application_id)
    )
    tasks = tasks_result.scalars().all()
    task = next(
        (t for t in tasks
         if doc_type_norm in _normalize_name(t.task_name)
         or _normalize_name(t.task_name) in doc_type_norm),
        None,
    )
    if task and task.document_id != doc.id:
        await db_update(db, ApplicationTask, task.id, {
            "document_id":  doc.id,
            "is_completed": True,
            "modified_by":  actor_id,
        })


def _to_response(doc: Document, task_id: uuid.UUID | None = None, task_name: str | None = None) -> DocumentResponse:
    return DocumentResponse(
        id               = doc.id,
        user_id          = doc.user_id,
        application_id   = doc.application_id,
        document_type_id = doc.document_type_id,
        name             = doc.file_name,
        file_size_bytes  = (doc.file_size_kb or 0) * 1024,
        file_type        = doc.file_format,
        status           = doc.status,
        document_type    = doc.document_type.name     if doc.document_type else None,
        category         = doc.document_type.category if doc.document_type else None,
        uploaded_at      = doc.created_at,
        verified_at      = doc.verified_at,
        rejection_reason = doc.rejection_reason,
        total_pages      = doc.total_pages,
        ocr_status       = doc.ocr_status,
        version          = doc.version,
        task_id          = task_id,
        task_name        = task_name,
    )


# ── GET /hr/cases/:applicationId/documents ────────────────────────────────────
# List all documents for a specific case. HR must own the case.

@hr_document_router.get(
    "/cases/{application_id}/documents",
    response_model=DocumentListResponse,
)
async def hr_list_documents(
    application_id: uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    # Check HR owns this case
    app_result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    application = app_result.scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    _assert_hr_access(application, current_user.user_id)

    # Superseded documents are retired versions — a replace/reupload leaves
    # the old row in place (status="superseded") purely for history, but it
    # is never the one a task points to and should never be something HR
    # reviews or verifies. Without this filter, every re-upload accumulates
    # another row here, so the same requirement can show up multiple times
    # (e.g. 3x "Educational Transcripts" after two re-uploads) — and HR could
    # end up verifying an old, no-longer-linked version instead of the
    # current one the employee's task actually points to.
    stmt = (
        select(Document)
        .options(joinedload(Document.document_type))
        .where(
            Document.application_id == application_id,
            Document.status != "superseded",
        )
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    # NEW — reverse lookup: which task (if any) currently has document_id
    # pointing at each of these documents? A document with no matching task
    # is either a genuine "Additional Document" or a stale/orphaned upload
    # that never got linked (or was superseded by a later re-upload) — this
    # is exactly the ambiguity that made two same-named "Passport Copy"
    # cards indistinguishable before. Built as one query + dict rather than
    # N+1 lookups per document.
    task_result = await db.execute(
        select(ApplicationTask.document_id, ApplicationTask.id, ApplicationTask.task_name)
        .where(
            ApplicationTask.application_id == application_id,
            ApplicationTask.document_id.isnot(None),
        )
    )
    task_by_doc_id = {row[0]: (row[1], row[2]) for row in task_result.all()}

    items = [
        _to_response(d, *task_by_doc_id.get(d.id, (None, None)))
        for d in docs
    ]
    return DocumentListResponse(items=items, total=len(items))


# ── POST /hr/documents/upload ─────────────────────────────────────────────────
# HR uploads a document on behalf of an employee (same as employee endpoint).

@hr_document_router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=201,
)
async def hr_upload_document(
    file:           UploadFile          = File(...),
    application_id: Optional[str]       = Form(None),
    document_type:  str                 = Form(...),
    category:       str                 = Form(...),
    db:             AsyncSession         = Depends(get_db),
    current_user = Depends(get_current_user),
):
    app_id = uuid.UUID(application_id) if application_id else None

    # Verify HR access if application_id provided
    if app_id:
        app_result = await db.execute(select(Application).where(Application.id == app_id))
        application = app_result.scalars().first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found.")
        _assert_hr_access(application, current_user.user_id)

        # Upload as the employee (not the HR user)
        return await upload_document(
            db, application.user_id, app_id, document_type, category, file
        )

    return await upload_document(
        db, current_user.user_id, None, document_type, category, file
    )


# ── POST /hr/cases/:applicationId/documents/upload ────────────────────────────
# Case-scoped upload — matches the /cases/{application_id}/... convention used
# by hr_task_routes.py and the GET /cases/{application_id}/documents route
# above. Same underlying upload_document() call as hr_upload_document(); this
# just makes application_id a required path param instead of an optional form
# field, for the Documents & Checklist screen's dropzone.

@hr_document_router.post(
    "/cases/{application_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=201,
)
async def hr_upload_document_for_case(
    application_id: uuid.UUID,
    file:           UploadFile  = File(...),
    document_type:  str         = Form(...),
    category:       str         = Form(...),
    db:             AsyncSession = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    app_result = await db.execute(select(Application).where(Application.id == application_id))
    application = app_result.scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    _assert_hr_access(application, current_user.user_id)

    # Upload as the employee (not the HR user) — same as hr_upload_document()
    return await upload_document(
        db, application.user_id, application_id, document_type, category, file
    )


# ── GET /hr/documents/:documentId ─────────────────────────────────────────────

@hr_document_router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
async def hr_get_document(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.application_id:
        app_result = await db.execute(select(Application).where(Application.id == doc.application_id))
        application = app_result.scalars().first()
        if application:
            _assert_hr_access(application, current_user.user_id)
    return _to_response(doc)


# ── GET /hr/documents/:documentId/view ────────────────────────────────────────

@hr_document_router.get("/documents/{document_id}/view")
async def hr_view_document(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    doc_info = await get_document_file_url(db, document_id, current_user.user_id)

    fmt = doc_info["file_format"].lower()
    media_types = {
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "png":  "image/png",
        "gif":  "image/gif",
        "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    media_type = media_types.get(fmt, "application/octet-stream")

    content, _ = await storage.get_file_bytes(doc_info["file_path"])

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{doc_info["file_name"]}"'},
    )

# ── PATCH /hr/documents/:documentId/verify ────────────────────────────────────
# HR marks a document as verified.

@hr_document_router.patch(
    "/documents/{document_id}/verify",
    response_model=DocumentResponse,
)
async def hr_verify_document(
    document_id:  uuid.UUID,
    payload:      dict = {},
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    await db_update(db, Document, document_id, {
        "status":      "verified",
        "verified_by": current_user.user_id,
        "verified_at": datetime.now(timezone.utc),
        "modified_by": current_user.user_id,
    })

    activity = DocumentActivity(
        document_id = document_id,
        action      = "verified",
        actor_id    = current_user.user_id,
        actor_type  = "hr_admin",
        note        = payload.get("note"),
        created_by  = current_user.user_id,
    )
    await db_create(db, activity)

    # Reload
    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == document_id)
    )
    doc = result.scalars().first()

    await _relink_task_to_document(db, doc, current_user.user_id)

    case_reference = None
    if doc.application_id:
        app_result = await db.execute(select(Application).where(Application.id == doc.application_id))
        app = app_result.scalars().first()
        case_reference = app.application_number if app else None

    await fire_document_verified(
        db,
        document_id     = doc.id,
        document_name   = doc.document_type.name if doc.document_type else "Document",
        application_id  = doc.application_id,
        case_reference  = case_reference,
        employee_id     = doc.user_id,
        verifier_id     = current_user.user_id,
    )

    return _to_response(doc)


# ── PATCH /hr/documents/:documentId/reject ───────────────────────────────────
# HR rejects a document with a reason.

@hr_document_router.patch(
    "/documents/{document_id}/reject",
    response_model=DocumentResponse,
)
async def hr_reject_document(
    document_id:  uuid.UUID,
    payload:      dict,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    if not payload.get("rejection_reason"):
        raise HTTPException(status_code=422, detail="rejection_reason is required.")

    await db_update(db, Document, document_id, {
        "status":           "rejected",
        "rejection_reason": payload["rejection_reason"],
        "modified_by":      current_user.user_id,
    })

    activity = DocumentActivity(
        document_id = document_id,
        action      = "rejected",
        actor_id    = current_user.user_id,
        actor_type  = "hr_admin",
        note        = payload["rejection_reason"],
        created_by  = current_user.user_id,
    )
    await db_create(db, activity)

    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == document_id)
    )
    doc = result.scalars().first()

    await _relink_task_to_document(db, doc, current_user.user_id)

    case_reference = None
    if doc.application_id:
        app_result = await db.execute(select(Application).where(Application.id == doc.application_id))
        app = app_result.scalars().first()
        case_reference = app.application_number if app else None

    await fire_document_rejected(
        db,
        document_id       = doc.id,
        document_name     = doc.document_type.name if doc.document_type else "Document",
        application_id    = doc.application_id,
        case_reference    = case_reference,
        employee_id       = doc.user_id,
        reviewer_id       = current_user.user_id,
        rejection_reason  = payload["rejection_reason"],
    )

    return _to_response(doc)


# ── POST /hr/documents/:documentId/request ────────────────────────────────────
# Re-request an EXISTING document (e.g. ask for a re-upload after rejection).
# For a brand-new request with no document yet, use
# POST /hr/cases/{application_id}/documents/requests (hr_document_request_routes.py)
# instead — both routes converge on hr_document_request_service so there's one
# real implementation (a DocumentRequest row + a Notification) behind each.

@hr_document_router.post("/documents/{document_id}/request")
async def hr_request_document(
    document_id:  uuid.UUID,
    payload:      dict = {},
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not doc.application_id:
        raise HTTPException(status_code=422, detail="Document is not attached to a case.")

    doc_name = doc.document_type.name if doc.document_type else "Document"

    request = await hr_create_document_request(
        db=db,
        application_id=doc.application_id,
        hr_user_id=current_user.user_id,
        payload=DocumentRequestCreate(
            document_name=doc_name,
            details=payload.get("message") or f"Please re-upload {doc_name}.",
            priority=DocumentRequestPriority.normal,
        ),
        document_id=document_id,
    )

    # Log alongside the existing DocumentActivity trail for this document
    # (DocumentActivity.document_id is NOT NULL, so this route — which always
    # has an existing document — keeps logging it; the brand-new-request path
    # in hr_document_request_routes.py has no document yet and can't).
    activity = DocumentActivity(
        document_id = document_id,
        action      = "document_requested",
        actor_id    = current_user.user_id,
        actor_type  = "hr_admin",
        note        = request.details,
        created_by  = current_user.user_id,
    )
    await db_create(db, activity)

    return {"success": True, "message": "Employee has been notified.", "request_id": str(request.id)}


# ── DELETE /hr/documents/:documentId ─────────────────────────────────────────

@hr_document_router.delete("/documents/{document_id}", status_code=204)
async def hr_delete_document(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    await db.delete(doc)
    await db.commit()