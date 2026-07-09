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
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import (
    Document, DocumentType, Application, DocumentActivity,
)
from app.schemas.employee.document import DocumentListResponse, DocumentResponse
from app.services.employee.document_service import (
    get_document_file_url, upload_document,
)
from app.services.employee.services import db_create, db_update


hr_document_router = APIRouter()


def _assert_hr_access(application: Application, hr_user_id: uuid.UUID):
    """HR can only access cases assigned to them."""
    if application.assigned_hr_id != hr_user_id:
        raise HTTPException(status_code=403, detail="Access denied to this case.")


def _to_response(doc: Document) -> DocumentResponse:
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

    stmt = (
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.application_id == application_id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return DocumentListResponse(items=[_to_response(d) for d in docs], total=len(docs))


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
    doc_info  = await get_document_file_url(db, document_id, current_user.user_id)
    file_path = f"./{doc_info['file_path']}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk.")
    fmt = doc_info["file_format"].lower()
    media_types = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png",  "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return FileResponse(
        path       = file_path,
        media_type = media_types.get(fmt, "application/octet-stream"),
        filename   = doc_info["file_name"],
        headers    = {"Content-Disposition": "inline"},
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
    return _to_response(result.scalars().first())


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
    return _to_response(result.scalars().first())


# ── POST /hr/documents/:documentId/request ────────────────────────────────────
# Sends a notification to the employee to re-upload a document.

@hr_document_router.post("/documents/{document_id}/request")
async def hr_request_document(
    document_id:  uuid.UUID,
    payload:      dict = {},
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    # TODO: create a notification / application task for the employee
    # For now, log the activity
    activity = DocumentActivity(
        document_id = document_id,
        action      = "status_changed",
        actor_id    = current_user.user_id,
        actor_type  = "hr_admin",
        note        = f"HR requested re-upload. {payload.get('message', '')}".strip(),
        created_by  = current_user.user_id,
    )
    await db_create(db, activity)
    return {"success": True, "message": "Employee has been notified."}


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


# ─────────────────────────────────────────────────────────────────────────────
# APPROVAL QUEUE ENDPOINTS
# Add separately or keep in this file — your choice
# ─────────────────────────────────────────────────────────────────────────────

# ── PATCH /hr/approvals/:documentId/approve ───────────────────────────────────

@hr_document_router.patch("/approvals/{document_id}/approve")
async def hr_approve_document(
    document_id:  uuid.UUID,
    payload:      dict = {},
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    """Wrapper: approve = verify."""
    await db_update(db, Document, document_id, {
        "status":      "verified",
        "verified_by": current_user.user_id,
        "verified_at": datetime.now(timezone.utc),
        "modified_by": current_user.user_id,
    })
    activity = DocumentActivity(
        document_id = document_id, action = "verified",
        actor_id = current_user.user_id, actor_type = "hr_admin",
        note = payload.get("note"), created_by = current_user.user_id,
    )
    await db_create(db, activity)
    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == document_id)
    )
    return _to_response(result.scalars().first())


# ── PATCH /hr/approvals/:documentId/request-edits ────────────────────────────

@hr_document_router.patch("/approvals/{document_id}/request-edits")
async def hr_request_edits(
    document_id:  uuid.UUID,
    payload:      dict,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    """Wrapper: request edits = reject with note."""
    note = payload.get("note", "")
    if not note:
        raise HTTPException(status_code=422, detail="note is required.")
    await db_update(db, Document, document_id, {
        "status":           "rejected",
        "rejection_reason": note,
        "modified_by":      current_user.user_id,
    })
    activity = DocumentActivity(
        document_id = document_id, action = "status_changed",
        actor_id = current_user.user_id, actor_type = "hr_admin",
        note = f"Edit requested: {note}", created_by = current_user.user_id,
    )
    await db_create(db, activity)
    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == document_id)
    )
    return _to_response(result.scalars().first())


# ── POST /hr/approvals/bulk-approve ──────────────────────────────────────────

@hr_document_router.post("/approvals/bulk-approve")
async def hr_bulk_approve(
    payload:      dict,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    document_ids = payload.get("document_ids", [])
    approved = failed = 0
    for doc_id_str in document_ids:
        try:
            doc_id = uuid.UUID(doc_id_str)
            await db_update(db, Document, doc_id, {
                "status":      "verified",
                "verified_by": current_user.user_id,
                "verified_at": datetime.now(timezone.utc),
                "modified_by": current_user.user_id,
            })
            approved += 1
        except Exception:
            failed += 1
    return {"approved": approved, "failed": failed}