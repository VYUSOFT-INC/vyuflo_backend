# app/services/employee/document_service.py

import uuid
import os
from datetime import datetime, timezone
from typing import Optional
from app.services.employee import storage
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload

from app.models.visamodels import Document, DocumentOCRField, DocumentType, ApplicationTask
from app.schemas.employee.document import DocumentResponse, DocumentListResponse
from app.services.employee.services import db_create, db_update


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _to_response(doc: Document) -> DocumentResponse:
    """Map ORM Document → DocumentResponse with frontend-friendly field names."""
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


async def _load_doc_with_type(db: AsyncSession, doc_id: uuid.UUID) -> Document:
    """Reload a Document with its document_type relationship."""
    result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.id == doc_id)
    )
    return result.scalars().first()


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────

async def list_documents(
    db:             AsyncSession,
    user_id:        uuid.UUID,
    application_id: Optional[uuid.UUID] = None,
) -> DocumentListResponse:
    stmt = (
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    if application_id:
        stmt = stmt.where(Document.application_id == application_id)

    result = await db.execute(stmt)
    docs   = result.scalars().all()
    return DocumentListResponse(items=[_to_response(d) for d in docs], total=len(docs))


# ─────────────────────────────────────────────────────────────────────────────
# GET BY ID
# ─────────────────────────────────────────────────────────────────────────────

async def get_document_by_id(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    document_id:     uuid.UUID,
) -> DocumentResponse:
    doc = await _load_doc_with_type(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return _to_response(doc)


# ─────────────────────────────────────────────────────────────────────────────
# GET FILE (for /view endpoint)
# ─────────────────────────────────────────────────────────────────────────────

async def get_document_file_url(
    db:      AsyncSession,
    doc_id:  uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    result = await db.execute(
        select(Document).where(Document.id == doc_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    return {
        "id":          doc.id,
        "file_name":   doc.file_name,
        "file_path":   doc.file_path,
        "file_format": doc.file_format,
    }


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD
# FIX: Step 5 now LINKS the document to the task but does NOT complete it.
#      Task completion happens only after the user confirms OCR in the viewer.
# ─────────────────────────────────────────────────────────────────────────────

async def upload_document(
    db:             AsyncSession,
    user_id:        uuid.UUID,
    application_id: Optional[uuid.UUID],
    document_type:  str,
    category:       str,
    file:           UploadFile,
) -> DocumentResponse:

    # 1. Find or create DocumentType
    result = await db.execute(
        select(DocumentType).where(DocumentType.name == document_type)
    )
    doc_type = result.scalars().first()
    if not doc_type:
        doc_type = DocumentType(
            name        = document_type,
            category    = category,
            description = f"Auto-created: {document_type}",
            created_by  = user_id,
        )
        doc_type = await db_create(db, doc_type)

    # 2. Read file
    content      = await file.read()
    file_size_kb = len(content) // 1024
    ext          = (file.filename or "file").rsplit(".", 1)[-1].lower()
    file_format  = ext if ext in ("pdf", "jpg", "jpeg", "png", "docx", "gif") else "pdf"
    if file_format == "jpeg":
        file_format = "jpg"

    # 3. Save to storage (local dev or S3 prod)
    safe_name    = os.path.basename(file.filename or f"document.{file_format}")
    storage_path = f"users/{user_id}/documents/{document_type}/{safe_name}"
    await storage.upload_file(
        content,
        storage_path,
        file.content_type or "application/octet-stream",
    )

    # 4. Create Document record
    doc = Document(
        user_id          = user_id,
        application_id   = application_id,
        document_type_id = doc_type.id,
        file_name        = file.filename,
        file_path        = storage_path,
        file_size_kb     = file_size_kb,
        file_format      = file_format,
        status           = "uploaded",
        ocr_status       = "not_started",
        version          = 1,
        is_draft         = False,
        created_by       = user_id,
    )
    doc = await db_create(db, doc)

    # 5. FIX — link document to task but DO NOT mark completed yet.
    #    Task completes only after confirm_document_ocr() is called,
    #    which happens when the user reviews + submits OCR fields in the viewer.
    if application_id:
        task_result = await db.execute(
            select(ApplicationTask).where(
                ApplicationTask.application_id == application_id,
                ApplicationTask.task_name.ilike(f"%{document_type}%"),
                ApplicationTask.is_completed == False,
            )
        )
        task = task_result.scalars().first()
        if task:
            await db_update(db, ApplicationTask, task.id, {
                "document_id": doc.id,   # link only — is_completed stays False
                "modified_by": user_id,
            })

    # Reload with relationship and return
    doc_with_type = await _load_doc_with_type(db, doc.id)
    return _to_response(doc_with_type)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIRM OCR
# Called by frontend after user reviews + submits OCR fields.
# Sets ocr_status=confirmed, status=pending_review, marks task completed.
# ─────────────────────────────────────────────────────────────────────────────

async def confirm_document_ocr(
    db:      AsyncSession,
    doc_id:  uuid.UUID,
    user_id: uuid.UUID,
) -> DocumentResponse:

    # 1. Load and authorize
    result = await db.execute(
        select(Document).where(Document.id == doc_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # 2. Mark document OCR as confirmed
    await db_update(db, Document, doc_id, {
        "ocr_status":  "confirmed",
        "status":      "pending_review",  # HR / attorney verifies next
        "modified_by": user_id,
    })

    # 3. Mark the linked task as completed
    task_result = await db.execute(
        select(ApplicationTask).where(
            ApplicationTask.document_id  == doc_id,
            ApplicationTask.is_completed == False,
        )
    )
    task = task_result.scalars().first()
    if task:
        await db_update(db, ApplicationTask, task.id, {
            "is_completed": True,
            "completed_at": datetime.now(timezone.utc),
            "completed_by": user_id,
            "modified_by":  user_id,
        })

    doc_updated = await _load_doc_with_type(db, doc_id)
    return _to_response(doc_updated)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# Deletes the file, OCR fields, and document record.
# Resets any linked task back to pending so the user can re-upload.
# ─────────────────────────────────────────────────────────────────────────────

async def delete_document(
    db:      AsyncSession,
    doc_id:  uuid.UUID,
    user_id: uuid.UUID,
) -> None:

    # 1. Load and authorize
    result = await db.execute(
        select(Document).where(Document.id == doc_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # 2. Reset any linked task back to pending
    task_result = await db.execute(
        select(ApplicationTask).where(
            ApplicationTask.document_id == doc_id
        )
    )
    task = task_result.scalars().first()
    if task:
        await db_update(db, ApplicationTask, task.id, {
            "document_id":  None,
            "is_completed": False,
            "completed_at": None,
            "completed_by": None,
            "modified_by":  user_id,
        })

    # 3. Delete OCR fields
    await db.execute(
        delete(DocumentOCRField).where(DocumentOCRField.document_id == doc_id)
    )

    # 4. Delete physical file from storage (don't block if it fails)
    try:
        await storage.delete_file(doc.file_path)
    except Exception:
        pass

    # 5. Delete document record and commit
    await db.execute(
        delete(Document).where(Document.id == doc_id)
    )
    await db.commit()