import uuid
import os
from datetime import datetime, timezone
from typing import Optional
from app.services.employee import storage
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, update
from sqlalchemy.orm import joinedload

from app.models.visamodels import Document, DocumentOCRField, DocumentType, ApplicationTask
from app.schemas.employee.document import DocumentResponse, DocumentListResponse
from app.services.employee.services import db_create, db_get_by_id, db_list, db_update
from app.services.attorney.document_request_service import fulfill_document_request



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


async def upload_document(
    db:              AsyncSession,
    user_id:         uuid.UUID,
    application_id:  Optional[uuid.UUID],
    document_type:   str,     # e.g. "passport"
    category:        str,     # e.g. "identity"
    file:            UploadFile,
    document_request_id: Optional[uuid.UUID] = None,   # ← ADD
    actor_id:            Optional[uuid.UUID] = None,
) -> DocumentResponse:
    creator_id = actor_id or user_id

    VALID_CATEGORIES = {"identity", "employment", "education", "legal", "personal", "other"}
    if category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
        )

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
    content   = await file.read()
    file_size_kb = len(content) // 1024
    ext       = (file.filename or "file").rsplit(".", 1)[-1].lower()
    file_format = ext if ext in ("pdf", "jpg", "jpeg", "png", "docx", "gif") else "pdf"
    if file_format == "jpeg":
        file_format = "jpg"

    # 3. Save file (local in dev, S3 in prod)
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
        created_by       = creator_id,
    )
    doc = await db_create(db, doc)

    from app.models.visamodels import DocumentActivity
    await db_create(db, DocumentActivity(
        document_id = doc.id,
        action      = "uploaded",
        actor_id    = creator_id,
        actor_type  = "attorney" if (actor_id and actor_id != user_id) else "user",
        note        = "Uploaded on behalf of client." if (actor_id and actor_id != user_id) else None,
        created_by  = creator_id,
    ))

    # 5. Auto-complete the matching task if application_id given
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
            from app.services.employee.services import db_update
            await db_update(db, ApplicationTask, task.id, {
                "is_completed": True,
                "completed_at": datetime.now(timezone.utc),
                "completed_by": user_id,
                "document_id":  doc.id,
                "modified_by":  user_id,
            })

    # Reload with relationship
    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == doc.id)
    )
    doc_with_type = result.scalars().first()
    if document_request_id:
        await fulfill_document_request(db, document_request_id, doc.id, user_id)

    return _to_response(doc_with_type)

# document_service.py — add this function
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
        "id":        doc.id,
        "file_name": doc.file_name,
        "file_path": doc.file_path,       # local path or S3 key
        "file_format": doc.file_format,   # "jpg", "png", "pdf"
    }

async def get_document_by_id(
    db: AsyncSession,
    current_user_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentResponse:
    """
    GET /documents/{document_id}
    """

    result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.id == document_id)
    )

    document = result.scalars().first()

    # Not found
    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # Security check
    if document.user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    return DocumentResponse(
        id=document.id,
        user_id=document.user_id,
        application_id=document.application_id,
        document_type_id=document.document_type_id,

        # frontend-friendly mapping
        name=document.file_name,
        file_size_bytes=document.file_size_kb * 1024,
        file_type=document.file_format,

        status=document.status,

        document_type=(
            document.document_type.name
            if document.document_type
            else None
        ),

        category=(
            document.document_type.category
            if document.document_type
            else None
        ),

        uploaded_at=document.created_at,
        verified_at=document.verified_at,
        rejection_reason=document.rejection_reason,
        total_pages=document.total_pages,
        ocr_status=document.ocr_status,
        version=document.version,
    )

