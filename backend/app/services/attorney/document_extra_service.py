# =============================================================================
# app/services/document_extra_service.py
#
# NEW service functions only — for the 7 new APIs.
# Your existing app/services/document_service.py is NOT touched.
#
# Reuses:
#   _to_response()     — imported from your existing document_service.py
#   db_create()        — imported from your existing services.py
#   db_update()        — imported from your existing services.py
#   Document model     — from visamodels.py
# =============================================================================

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.models.visamodels import (
    Document,
    DocumentActivity,
    DocumentPage,
)
from app.schemas.attorney.document_extra import (
    DocumentActivityListResponse,
    DocumentActivityResponse,
    DocumentPageListResponse,
    DocumentPageResponse,
    DocumentStatus,
    DocumentVersionListResponse,
    DocumentVersionResponse,
)
# Reuse your existing mapper — no duplication
from app.schemas.employee.document import DocumentResponse
from app.services.employee.document_service import _to_response
from app.services.employee.services import db_create, db_update
from app.models.visamodels import Application


# ─────────────────────────────────────────────────────────────────────────────
# GET /documents/{id}/versions
# ─────────────────────────────────────────────────────────────────────────────

async def get_document_versions(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> DocumentVersionListResponse:
    """
    Returns all versions of a document by walking the parent_document_id chain.
    Ownership checked on the requested document.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Walk to root (version 1 has no parent)
    root_id = doc.parent_document_id or doc.id

    # All docs sharing the same root = full version chain
    stmt = select(Document).where(
        (Document.id == root_id) |
        (Document.parent_document_id == root_id)
    ).order_by(Document.version.asc())

    result = await db.execute(stmt)
    docs   = result.scalars().all()

    items = [
        DocumentVersionResponse(
            id              = d.id,
            version         = d.version,
            name            = d.file_name,
            file_size_bytes = (d.file_size_kb or 0) * 1024,
            file_type       = d.file_format,
            status          = d.status,
            uploaded_at     = d.created_at,
        )
        for d in docs
    ]
    return DocumentVersionListResponse(items=items, total=len(items))


# ─────────────────────────────────────────────────────────────────────────────
# GET /documents/{id}/activity
# ─────────────────────────────────────────────────────────────────────────────

async def get_document_activity(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> DocumentActivityListResponse:
    """
    Returns the audit log for a document.
    Ownership checked — attorney/HR bypass handled at router via RBAC.
    """
    result = await db.execute(
        select(Document.user_id).where(Document.id == document_id)
    )
    owner_id = result.scalar_one_or_none()
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if owner_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    stmt = (
        select(DocumentActivity)
        .where(DocumentActivity.document_id == document_id)
        .order_by(DocumentActivity.created_at.desc())
    )
    result  = await db.execute(stmt)
    records = result.scalars().all()

    items = [
        DocumentActivityResponse(
            id         = r.id,
            action     = r.action,
            actor_id   = r.actor_id,
            actor_type = r.actor_type,
            note       = r.note,
            created_at = r.created_at,
        )
        for r in records
    ]
    return DocumentActivityListResponse(items=items, total=len(items))


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /documents/{id}
# ─────────────────────────────────────────────────────────────────────────────

async def delete_document(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> dict:
    """
    Soft delete — sets status = 'missing', is_draft = True.
    Blocks deletion of verified documents.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if doc.status == "verified":
        raise HTTPException(
            status_code=409,
            detail="Verified documents cannot be deleted. Contact your attorney or HR.",
        )

    await db_update(db, Document, document_id, {
        "status":      "missing",
        "is_draft":    True,
        "modified_by": user_id,
    })

    return {"detail": "Document deleted.", "document_id": str(document_id)}


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /documents/{id}/status
# ─────────────────────────────────────────────────────────────────────────────

async def update_document_status(
    db:               AsyncSession,
    document_id:      uuid.UUID,
    reviewer_id:      uuid.UUID,
    new_status:       DocumentStatus,
    rejection_reason: Optional[str] = None,
) -> DocumentResponse:
    """
    Attorney / HR / Admin: verify or reject a document.
    """
    result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if new_status == DocumentStatus.rejected and not rejection_reason:
        raise HTTPException(
            status_code=422,
            detail="rejection_reason is required when rejecting a document.",
        )

    updates: dict = {
        "status":      new_status,
        "modified_by": reviewer_id,
    }

    if new_status == DocumentStatus.verified:
        updates["verified_by"]      = reviewer_id
        updates["verified_at"]      = datetime.now(timezone.utc)
        updates["rejection_reason"] = None

    if new_status == DocumentStatus.rejected:
        updates["rejection_reason"] = rejection_reason
        updates["verified_by"]      = None
        updates["verified_at"]      = None

    await db_update(db, Document, document_id, updates)

    # Reload with relationship for the response
    result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.id == document_id)
    )
    return _to_response(result.scalars().first())


# ─────────────────────────────────────────────────────────────────────────────
# GET /documents/{id}/pages
# ─────────────────────────────────────────────────────────────────────────────

async def get_document_pages(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> DocumentPageListResponse:
    """
    Returns ordered page list with thumbnail URLs for the OCR page strip.
    """
    result = await db.execute(
        select(Document.user_id).where(Document.id == document_id)
    )
    owner_id = result.scalar_one_or_none()
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if owner_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    stmt = (
        select(DocumentPage)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number.asc())
    )
    result = await db.execute(stmt)
    pages  = result.scalars().all()

    items = [
        DocumentPageResponse(
            id             = p.id,
            document_id    = p.document_id,
            page_number    = p.page_number,
            thumbnail_url  = p.thumbnail_url,
            image_url      = p.image_url,
            ocr_confidence = p.ocr_confidence,
        )
        for p in pages
    ]
    return DocumentPageListResponse(items=items, total=len(items))


# ─────────────────────────────────────────────────────────────────────────────
# POST /documents/{id}/ocr/trigger
# ─────────────────────────────────────────────────────────────────────────────

async def trigger_ocr(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> dict:
    """
    Sets ocr_status = 'processing'.
    Actual OCR work is dispatched by the router via BackgroundTasks.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if doc.ocr_status == "processing":
        raise HTTPException(status_code=409, detail="OCR is already in progress.")

    await db_update(db, Document, document_id, {
        "ocr_status":  "processing",
        "modified_by": user_id,
    })

    return {
        "detail":      "OCR processing started.",
        "document_id": str(document_id),
        "ocr_status":  "processing",
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /documents  (filtered version)
# ─────────────────────────────────────────────────────────────────────────────

async def list_documents_filtered(
    db:             AsyncSession,
    user_id:        uuid.UUID,
    application_id: Optional[uuid.UUID] = None,
    status:         Optional[str]       = None,
    category:       Optional[str]       = None,
    document_type:  Optional[str]       = None,
):
    """
    Extended list with status / category / document_type filters.
    Separate from your existing list_documents() — that one is untouched.
    Use this one from the new router, or swap in gradually.
    """
    from app.models.visamodels import DocumentType as DocTypeModel
    from app.schemas.employee.document import DocumentListResponse

    stmt = (
    select(Document)
    .join(Application, Document.application_id == Application.id)
    .options(joinedload(Document.document_type))
    .where(Application.assigned_attorney_id == user_id)   # ← attorney's scope
    .order_by(Document.created_at.desc())
)
    # stmt = (
        # select(Document)
        # .options(joinedload(Document.document_type))
        # .where(Document.user_id == user_id)
        # .order_by(Document.created_at.desc())
    # )

    if application_id:
        stmt = stmt.where(Document.application_id == application_id)

    if status:
        stmt = stmt.where(Document.status == status)

    if category or document_type:
        stmt = stmt.join(DocTypeModel, Document.document_type_id == DocTypeModel.id)
        if category:
            stmt = stmt.where(DocTypeModel.category == category)
        if document_type:
            stmt = stmt.where(DocTypeModel.name == document_type)

    result = await db.execute(stmt)
    docs   = result.scalars().unique().all()

    return DocumentListResponse(
        items=[_to_response(d) for d in docs],
        total=len(docs),
    )
# ─────────────────────────────────────────────────────────────────────────────
# GET /documents/my-rejected
# ─────────────────────────────────────────────────────────────────────────────

async def get_my_rejected_documents(
    db:      AsyncSession,
    user_id: uuid.UUID,
) -> list:
    """
    Returns all rejected documents for the logged-in client.
    Used for the 'Action Required' badge + list on the client portal.
    """
    from app.schemas.attorney.document_extra import RejectedDocumentResponse

    stmt = (
        select(Document)
        .where(
            Document.user_id == user_id,
            Document.status  == "rejected",
        )
        .order_by(Document.updated_at.desc())
    )
    result = await db.execute(stmt)
    docs   = result.scalars().all()

    return [
        RejectedDocumentResponse(
            id               = d.id,
            file_name        = d.file_name,
            rejection_reason = d.rejection_reason,
            status           = d.status,
            updated_at       = d.updated_at,
        )
        for d in docs
    ]