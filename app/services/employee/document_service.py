# # app/services/employee/document_service.py sai

# import uuid
# import os
# from datetime import datetime, timezone
# from typing import Optional
# from app.core.config import settings
# from app.services.employee import storage
# from fastapi import HTTPException, UploadFile
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import delete, select
# from sqlalchemy.orm import joinedload

# from app.models.visamodels import Document, DocumentOCRField, DocumentType, ApplicationTask
# from app.schemas.employee.document import DocumentResponse, DocumentListResponse
# from app.services.employee.services import db_create, db_update


# # ─────────────────────────────────────────────────────────────────────────────
# # INTERNAL HELPER
# # ─────────────────────────────────────────────────────────────────────────────

# def _to_response(doc: Document) -> DocumentResponse:
#     """Map ORM Document → DocumentResponse with frontend-friendly field names."""
#     return DocumentResponse(
#         id               = doc.id,
#         user_id          = doc.user_id,
#         application_id   = doc.application_id,
#         document_type_id = doc.document_type_id,
#         name             = doc.file_name,
#         file_size_bytes  = (doc.file_size_kb or 0) * 1024,
#         file_type        = doc.file_format,
#         status           = doc.status,
#         document_type    = doc.document_type.name     if doc.document_type else None,
#         category         = doc.document_type.category if doc.document_type else None,
#         uploaded_at      = doc.created_at,
#         verified_at      = doc.verified_at,
#         rejection_reason = doc.rejection_reason,
#         total_pages      = doc.total_pages,
#         ocr_status       = doc.ocr_status,
#         version          = doc.version,
#     )


# async def _load_doc_with_type(db: AsyncSession, doc_id: uuid.UUID) -> Document:
#     """Reload a Document with its document_type relationship."""
#     result = await db.execute(
#         select(Document)
#         .options(joinedload(Document.document_type))
#         .where(Document.id == doc_id)
#     )
#     return result.scalars().first()


# # ─────────────────────────────────────────────────────────────────────────────
# # LIST
# # ─────────────────────────────────────────────────────────────────────────────

# async def list_documents(
#     db:             AsyncSession,
#     user_id:        uuid.UUID,
#     application_id: Optional[uuid.UUID] = None,
# ) -> DocumentListResponse:
#     stmt = (
#         select(Document)
#         .options(joinedload(Document.document_type))
#         .where(Document.user_id == user_id)
#         .order_by(Document.created_at.desc())
#     )
#     if application_id:
#         stmt = stmt.where(Document.application_id == application_id)

#     result = await db.execute(stmt)
#     docs   = result.scalars().all()
#     return DocumentListResponse(items=[_to_response(d) for d in docs], total=len(docs))


# # ─────────────────────────────────────────────────────────────────────────────
# # GET BY ID
# # ─────────────────────────────────────────────────────────────────────────────

# async def get_document_by_id(
#     db:              AsyncSession,
#     current_user_id: uuid.UUID,
#     document_id:     uuid.UUID,
# ) -> DocumentResponse:
#     doc = await _load_doc_with_type(db, document_id)
#     if not doc:
#         raise HTTPException(status_code=404, detail="Document not found.")
#     if doc.user_id != current_user_id:
#         raise HTTPException(status_code=403, detail="Access denied.")
#     return _to_response(doc)


# # # ─────────────────────────────────────────────────────────────────────────────
# # # GET FILE (for /view endpoint)
# # # ─────────────────────────────────────────────────────────────────────────────

# # async def get_document_file_url(
# #     db:      AsyncSession,
# #     doc_id:  uuid.UUID,
# #     user_id: uuid.UUID,
# # ) -> dict:
# #     result = await db.execute(
# #         select(Document).where(Document.id == doc_id)
# #     )
# #     doc = result.scalars().first()
# #     if not doc:
# #         raise HTTPException(status_code=404, detail="Document not found.")
# #     if doc.user_id != user_id:
# #         raise HTTPException(status_code=403, detail="Access denied.")

# #     return {
# #         "id":          doc.id,
# #         "file_name":   doc.file_name,
# #         "file_path":   doc.file_path,
# #         "file_format": doc.file_format,
# #     }

# # document_service.py
# import uuid
# from fastapi import HTTPException
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.core_permissions import get_effective_permissions
# from app.models.visamodels import Document, Application, EmployerEmployee


# async def get_document_file_url(
#     db:      AsyncSession,
#     doc_id:  uuid.UUID,
#     user_id: uuid.UUID,
# ) -> dict:
#     result = await db.execute(select(Document).where(Document.id == doc_id))
#     doc = result.scalars().first()
#     if not doc:
#         raise HTTPException(status_code=404, detail="Document not found.")

#     if not await _can_access_document(db, doc, user_id):
#         raise HTTPException(status_code=403, detail="Access denied.")

#     return {
#         "id":          doc.id,
#         "file_name":   doc.file_name,
#         "file_path":   doc.file_path,
#         "file_format": doc.file_format,
#     }


# async def _can_access_document(db: AsyncSession, doc, user_id: uuid.UUID) -> bool:
#     """
#     Two-layer authorization:
#       Layer 1 (permission) — does the user hold a documents.view_* capability?
#       Layer 2 (scope)      — is THIS specific document within that capability's reach?
#     """
#     perms = await get_effective_permissions(user_id, db)

#     # view_all — admin tier: everything, no scoping
#     if "documents.view_all" in perms:
#         return True

#     # view_own — the employee who owns this document
#     if "documents.view_own" in perms and doc.user_id == user_id:
#         return True

#     # view_team — HR: linked as this employee's employer, OR assigned to the case
#     if "documents.view_team" in perms:
#         if await _is_my_employee(db, hr_user_id=user_id, employee_id=doc.user_id):
#             return True
#         if doc.application_id and await _is_assigned_hr(db, doc.application_id, user_id):
#             return True

#     # view_assigned — attorney assigned to this document's case
#     if "documents.view_assigned" in perms and doc.application_id:
#         if await _is_assigned_attorney(db, doc.application_id, user_id):
#             return True

#     return False


# async def _is_my_employee(db: AsyncSession, hr_user_id: uuid.UUID, employee_id: uuid.UUID) -> bool:
#     """True if an active EmployerEmployee link exists (HR ↔ employee)."""
#     row = await db.execute(
#         select(EmployerEmployee.id).where(
#             EmployerEmployee.employer_id == hr_user_id,
#             EmployerEmployee.employee_id == employee_id,
#             EmployerEmployee.is_active == True,   # noqa: E712
#         ).limit(1)
#     )
#     return row.scalar_one_or_none() is not None


# async def _is_assigned_hr(db: AsyncSession, application_id: uuid.UUID, viewer_id: uuid.UUID) -> bool:
#     """True if this HR user is explicitly assigned to the application."""
#     row = await db.execute(
#         select(Application.assigned_hr_id).where(Application.id == application_id)
#     )
#     assigned = row.scalar_one_or_none()
#     return assigned is not None and assigned == viewer_id


# async def _is_assigned_attorney(db: AsyncSession, application_id: uuid.UUID, viewer_id: uuid.UUID) -> bool:
#     """True if this attorney is assigned to the application."""
#     row = await db.execute(
#         select(Application.assigned_attorney_id).where(Application.id == application_id)
#     )
#     assigned = row.scalar_one_or_none()
#     return assigned is not None and assigned == viewer_id


# # ─────────────────────────────────────────────────────────────────────────────
# # UPLOAD
# # FIX: Step 5 now LINKS the document to the task but does NOT complete it.
# #      Task completion happens only after the user confirms OCR in the viewer.
# # ─────────────────────────────────────────────────────────────────────────────

# async def upload_document(
#     db:             AsyncSession,
#     user_id:        uuid.UUID,
#     application_id: Optional[uuid.UUID],
#     document_type:  str,
#     category:       str,
#     file:           UploadFile,
# ) -> DocumentResponse:

#     # 1. Find or create DocumentType
#     result = await db.execute(
#         select(DocumentType).where(DocumentType.name == document_type)
#     )
#     doc_type = result.scalars().first()
#     if not doc_type:
#         doc_type = DocumentType(
#             name        = document_type,
#             category    = category,
#             description = f"Auto-created: {document_type}",
#             created_by  = user_id,
#         )
#         doc_type = await db_create(db, doc_type)

#     # 2. Read file
#     content      = await file.read()
#     file_size_kb = len(content) // 1024
#     ext          = (file.filename or "file").rsplit(".", 1)[-1].lower()
#     file_format  = ext if ext in ("pdf", "jpg", "jpeg", "png", "docx", "gif") else "pdf"
#     if file_format == "jpeg":
#         file_format = "jpg"

#     # 3. Save to storage (local dev or S3 prod)
#     safe_name    = os.path.basename(file.filename or f"document.{file_format}")
#     storage_prefix = settings.STORAGE_PREFIX
#     storage_path = f"{storage_prefix}/users/{user_id}/documents/{document_type}/{safe_name}"
#     await storage.upload_file(
#         content,
#         storage_path,
#         file.content_type or "application/octet-stream",
#     )

#     # 4. Create Document record
#     doc = Document(
#         user_id          = user_id,
#         application_id   = application_id,
#         document_type_id = doc_type.id,
#         file_name        = file.filename,
#         file_path        = storage_path,
#         file_size_kb     = file_size_kb,
#         file_format      = file_format,
#         status           = "uploaded",
#         ocr_status       = "not_started",
#         version          = 1,
#         is_draft         = False,
#         created_by       = user_id,
#     )
#     doc = await db_create(db, doc)

#     # 5. FIX — link document to task but DO NOT mark completed yet.
#     #    Task completes only after confirm_document_ocr() is called,
#     #    which happens when the user reviews + submits OCR fields in the viewer.
#     if application_id:
#         task_result = await db.execute(
#             select(ApplicationTask).where(
#                 ApplicationTask.application_id == application_id,
#                 ApplicationTask.task_name.ilike(f"%{document_type}%"),
#                 ApplicationTask.is_completed == False,
#             )
#         )
#         task = task_result.scalars().first()
#         if task:
#             await db_update(db, ApplicationTask, task.id, {
#                 "document_id": doc.id,   # link only — is_completed stays False
#                 "modified_by": user_id,
#             })

#     # Reload with relationship and return
#     doc_with_type = await _load_doc_with_type(db, doc.id)
#     return _to_response(doc_with_type) 

# # ─────────────────────────────────────────────────────────────────────────────
# # CONFIRM OCR
# # Called by frontend after user reviews + submits OCR fields.
# # Sets ocr_status=confirmed, status=pending_review, marks task completed.
# # ─────────────────────────────────────────────────────────────────────────────

# async def confirm_document_ocr(
#     db:      AsyncSession,
#     doc_id:  uuid.UUID,
#     user_id: uuid.UUID,
# ) -> DocumentResponse:

#     # 1. Load and authorize
#     result = await db.execute(
#         select(Document).where(Document.id == doc_id)
#     )
#     doc = result.scalars().first()
#     if not doc:
#         raise HTTPException(status_code=404, detail="Document not found.")
#     if doc.user_id != user_id:
#         raise HTTPException(status_code=403, detail="Access denied.")

#     # 2. Mark document OCR as confirmed
#     await db_update(db, Document, doc_id, {
#         "ocr_status":  "confirmed",
#         "status":      "pending_review",  # HR / attorney verifies next
#         "modified_by": user_id,
#     })

#     # 3. Mark the linked task as completed
#     task_result = await db.execute(
#         select(ApplicationTask).where(
#             ApplicationTask.document_id  == doc_id,
#             ApplicationTask.is_completed == False,
#         )
#     )
#     task = task_result.scalars().first()
#     if task:
#         await db_update(db, ApplicationTask, task.id, {
#             "is_completed": True,
#             "completed_at": datetime.now(timezone.utc),
#             "completed_by": user_id,
#             "modified_by":  user_id,
#         })

#     doc_updated = await _load_doc_with_type(db, doc_id)
#     return _to_response(doc_updated)


# # ─────────────────────────────────────────────────────────────────────────────
# # DELETE
# # Deletes the file, OCR fields, and document record.
# # Resets any linked task back to pending so the user can re-upload.
# # ─────────────────────────────────────────────────────────────────────────────

# async def delete_document(
#     db:      AsyncSession,
#     doc_id:  uuid.UUID,
#     user_id: uuid.UUID,
# ) -> None:

#     # 1. Load and authorize
#     result = await db.execute(
#         select(Document).where(Document.id == doc_id)
#     )
#     doc = result.scalars().first()
#     if not doc:
#         raise HTTPException(status_code=404, detail="Document not found.")
#     if doc.user_id != user_id:
#         raise HTTPException(status_code=403, detail="Access denied.")

#     # 2. Reset any linked task back to pending
#     task_result = await db.execute(
#         select(ApplicationTask).where(
#             ApplicationTask.document_id == doc_id
#         )
#     )
#     task = task_result.scalars().first()
#     if task:
#         await db_update(db, ApplicationTask, task.id, {
#             "document_id":  None,
#             "is_completed": False,
#             "completed_at": None,
#             "completed_by": None,
#             "modified_by":  user_id,
#         })

#     # 3. Delete OCR fields
#     await db.execute(
#         delete(DocumentOCRField).where(DocumentOCRField.document_id == doc_id)
#     )

#     # 4. Delete physical file from storage (don't block if it fails)
#     try:
#         await storage.delete_file(doc.file_path)
#     except Exception:
#         pass

#     # 5. Delete document record and commit
#     await db.execute(
#         delete(Document).where(Document.id == doc_id)
#     )
#     await db.commit()



# async def reuse_document_for_case(
#     db:              AsyncSession,
#     user_id:         uuid.UUID,
#     source_document_id: uuid.UUID,
#     application_id:  uuid.UUID,
# ) -> DocumentResponse:
#     """Attach an existing Hub document to a new case WITHOUT re-uploading —
#     duplicates the storage object so the two Document rows are fully
#     independent (safe to delete one without breaking the other)."""

#     result = await db.execute(select(Document).where(Document.id == source_document_id))
#     src = result.scalars().first()
#     if not src:
#         raise HTTPException(status_code=404, detail="Source document not found.")
#     if src.user_id != user_id:
#         raise HTTPException(status_code=403, detail="Access denied.")

#     # Duplicate the physical file under a case-scoped key
#     safe_name   = os.path.basename(src.file_name)
#     storage_prefix = settings.STORAGE_PREFIX
#     new_path = f"{storage_prefix}/users/{user_id}/documents/{application_id}/{safe_name}"
#     await storage.copy_file(src.file_path, new_path)

#     new_doc = Document(
#         user_id           = user_id,
#         application_id    = application_id,
#         document_type_id  = src.document_type_id,
#         file_name         = src.file_name,
#         file_path         = new_path,
#         file_size_kb      = src.file_size_kb,
#         file_format       = src.file_format,
#         total_pages       = src.total_pages,
#         status            = "uploaded",       # fresh — needs this case's own review
#         ocr_status        = src.ocr_status,    # carry over — no need to redo OCR
#         ocr_confidence    = src.ocr_confidence,
#         version           = 1,
#         parent_document_id = src.id,           # traceability back to the Hub original
#         is_draft          = False,
#         created_by        = user_id,
#     )
#     new_doc = await db_create(db, new_doc)

#     # Copy over confirmed OCR fields too, so the student doesn't redo review
#     fields_result = await db.execute(
#         select(DocumentOCRField).where(DocumentOCRField.document_id == src.id)
#     )
#     for f in fields_result.scalars().all():
#         await db_create(db, DocumentOCRField(
#             document_id       = new_doc.id,
#             field_name        = f.field_name,
#             extracted_value   = f.extracted_value,
#             confidence_score  = f.confidence_score,
#             is_confirmed      = f.is_confirmed,
#             needs_review      = f.needs_review,
#             created_by        = user_id,
#         ))

#     # Link to the matching task, same as a fresh upload
#     task_result = await db.execute(
#         select(ApplicationTask).where(
#             ApplicationTask.application_id == application_id,
#             ApplicationTask.task_name.ilike(f"%{src.document_type.name if src.document_type else ''}%"),
#             ApplicationTask.is_completed == False,
#         )
#     )
#     task = task_result.scalars().first()
#     if task:
#         await db_update(db, ApplicationTask, task.id, {
#             "document_id": new_doc.id,
#             "modified_by": user_id,
#         })

#     doc_with_type = await _load_doc_with_type(db, new_doc.id)
#     return _to_response(doc_with_type)


# async def list_hub_documents(
#     db:      AsyncSession,
#     user_id: uuid.UUID,
#     search:  Optional[str] = None,
# ) -> DocumentListResponse:
#     """All of a user's documents across every case — the picker's 'From Hub' tab.
#     Scoped to user_id — a student only ever sees their own uploads, never
#     another user's documents, regardless of search term."""
#     stmt = (
#         select(Document)
#         .options(joinedload(Document.document_type))
#         .where(Document.user_id == user_id)   # ← this line is what guarantees no cross-user leakage
#         .order_by(Document.created_at.desc())
#     )
#     result = await db.execute(stmt)
#     docs = result.scalars().all()

#     if search:
#         s = search.lower()
#         docs = [d for d in docs if s in (d.file_name or "").lower()
#                 or s in (d.document_type.name.lower() if d.document_type else "")]

#     return DocumentListResponse(items=[_to_response(d) for d in docs], total=len(docs))


# app/services/employee/document_service.py

import uuid
import os
from datetime import datetime, timezone
from typing import Optional
from app.core.config import settings
from app.services.employee import storage
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload

from app.core.core_permissions import get_effective_permissions
from app.models.visamodels import (
    Document, DocumentOCRField, DocumentType, ApplicationTask,
    Application, EmployerEmployee,
)
from app.schemas.employee.document import DocumentResponse, DocumentListResponse
from app.services.employee.services import (
    db_create, db_update, db_delete, db_get_by_id, db_get_by_field, db_list,
)
from app.services.employee.notification_service import fire_document_uploaded


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


async def _load_doc_with_type(db: AsyncSession, doc_id: uuid.UUID) -> Optional[Document]:
    """Reload a Document with its document_type relationship.
    Kept as a raw query — db_get_by_id has no option to eager-load a
    relationship, and every call site here needs document_type populated
    for _to_response() to fill in document_type/category correctly."""
    result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.id == doc_id)
    )
    return result.scalars().first()


async def _find_task(
    db: AsyncSession,
    *,
    application_id: Optional[uuid.UUID] = None,
    document_id:    Optional[uuid.UUID] = None,
    task_name_like: Optional[str]       = None,
    only_incomplete: bool = False,
) -> Optional[ApplicationTask]:
    """Shared task lookup — wraps db_list so every call site (upload, confirm,
    delete, reuse) builds its filter list the same way instead of hand-rolling
    a fresh select() each time."""
    filters = []
    if application_id is not None:
        filters.append(ApplicationTask.application_id == application_id)
    if document_id is not None:
        filters.append(ApplicationTask.document_id == document_id)
    if task_name_like:
        filters.append(ApplicationTask.task_name.ilike(f"%{task_name_like}%"))
    if only_incomplete:
        filters.append(ApplicationTask.is_completed == False)  # noqa: E712

    rows = await db_list(db, ApplicationTask, filters=filters, limit=1)
    return rows[0] if rows else None



def _collapse_hub_families(docs: list[Document]) -> list[Document]:
    """One card per physical file in the Hub view.

    reuse_document_for_case() deliberately COPIES a file into a new case-scoped
    row with parent_document_id -> the original (see that function's docstring
    on why: each case needs an independent, safely-deletable copy). Good for
    isolation, but it means the Hub would otherwise list the same document once
    per case it's been reused into. Keep only family roots (the original
    upload); hide reuse-copies. An orphan whose parent was deleted is treated
    as its own root so it never silently disappears from the Hub.
    """
    ids = {d.id for d in docs}
    return [
        d for d in docs
        if d.parent_document_id is None or d.parent_document_id not in ids
    ]
# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────

# async def list_documents(
#     db:             AsyncSession,
#     user_id:        uuid.UUID,
#     application_id: Optional[uuid.UUID] = None,
# ) -> DocumentListResponse:
#     """Kept as a raw query — needs joinedload(document_type) for _to_response,
#     which db_list can't do."""
#     stmt = (
#         select(Document)
#         .options(joinedload(Document.document_type))
#         .where(Document.user_id == user_id)
#         .order_by(Document.created_at.desc())
#     )
#     if application_id:
#         stmt = stmt.where(Document.application_id == application_id)

#     result = await db.execute(stmt)
#     docs   = result.scalars().all()
#     return DocumentListResponse(items=[_to_response(d) for d in docs], total=len(docs))
async def list_documents(
    db:             AsyncSession,
    user_id:        uuid.UUID,
    application_id: Optional[uuid.UUID] = None,
) -> DocumentListResponse:
    """Kept as a raw query — needs joinedload(document_type) for _to_response,
    which db_list can't do."""
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

    if application_id is None:              # ← NEW: Hub-wide view — collapse reuse-copies
        docs = _collapse_hub_families(docs)

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
# GET FILE (for /view endpoint) — role-aware access (owner / HR / attorney / admin)
# ─────────────────────────────────────────────────────────────────────────────

async def get_document_file_url(
    db:      AsyncSession,
    doc_id:  uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    doc = await db_get_by_id(db, Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not await _can_access_document(db, doc, user_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    return {
        "id":          doc.id,
        "file_name":   doc.file_name,
        "file_path":   doc.file_path,
        "file_format": doc.file_format,
    }


async def _can_access_document(db: AsyncSession, doc: Document, user_id: uuid.UUID) -> bool:
    """
    Two-layer authorization:
      Layer 1 (permission) — does the user hold a documents.view_* capability?
      Layer 2 (scope)      — is THIS specific document within that capability's reach?
    """
    perms = await get_effective_permissions(user_id, db)

    # view_all — admin tier: everything, no scoping
    if "documents.view_all" in perms:
        return True

    # view_own — the employee who owns this document
    if "documents.view_own" in perms and doc.user_id == user_id:
        return True

    # view_team — HR: linked as this employee's employer, OR assigned to the case
    if "documents.view_team" in perms:
        if await _is_my_employee(db, hr_user_id=user_id, employee_id=doc.user_id):
            return True
        if doc.application_id and await _is_assigned_hr(db, doc.application_id, user_id):
            return True

    # view_assigned — attorney assigned to this document's case
    if "documents.view_assigned" in perms and doc.application_id:
        if await _is_assigned_attorney(db, doc.application_id, user_id):
            return True

    return False


async def _is_my_employee(db: AsyncSession, hr_user_id: uuid.UUID, employee_id: uuid.UUID) -> bool:
    """True if an active EmployerEmployee link exists (HR ↔ employee)."""
    rows = await db_list(db, EmployerEmployee, filters=[
        EmployerEmployee.employer_id == hr_user_id,
        EmployerEmployee.employee_id == employee_id,
        EmployerEmployee.is_active == True,  # noqa: E712
    ], limit=1)
    return len(rows) > 0


async def _is_assigned_hr(db: AsyncSession, application_id: uuid.UUID, viewer_id: uuid.UUID) -> bool:
    """True if this HR user is explicitly assigned to the application."""
    app = await db_get_by_id(db, Application, application_id)
    return app is not None and app.assigned_hr_id == viewer_id


async def _is_assigned_attorney(db: AsyncSession, application_id: uuid.UUID, viewer_id: uuid.UUID) -> bool:
    """True if this attorney is assigned to the application."""
    app = await db_get_by_id(db, Application, application_id)
    return app is not None and app.assigned_attorney_id == viewer_id


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD
# Step 5 LINKS the document to the task but does NOT complete it.
# Task completion happens only after the user confirms OCR in the viewer.
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
    doc_type = await db_get_by_field(db, DocumentType, "name", document_type)
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
    storage_prefix = settings.STORAGE_PREFIX
    storage_path = f"{storage_prefix}/users/{user_id}/documents/{document_type}/{safe_name}"
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

    # 5. Link document to task but DO NOT mark completed yet.
    #    Task completes only after confirm_document_ocr() is called.
    if application_id:
        task = await _find_task(
            db,
            application_id=application_id,
            task_name_like=document_type,
            only_incomplete=True,
        )
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

    # 1. Load and authorize — must eager-load document_type since we need
    #    doc.document_type.name below for the notification title, and
    #    application_id to look up who to notify.
    doc = await _load_doc_with_type(db, doc_id)
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
    task = await _find_task(db, document_id=doc_id, only_incomplete=True)
    if task:
        await db_update(db, ApplicationTask, task.id, {
            "is_completed": True,
            "completed_at": datetime.now(timezone.utc),
            "completed_by": user_id,
            "modified_by":  user_id,
        })

    # 4. Notify HR / attorney — fired HERE (not at raw upload time) because
    #    this is the moment status flips to "pending_review" and the document
    #    actually becomes something they can act on. Covers both the direct-
    #    upload path and the Hub-reuse path, since both funnel through this
    #    same confirm step.
    if doc.application_id:
        application = await db_get_by_id(db, Application, doc.application_id)
        if application:
            await fire_document_uploaded(
                db,
                document_id=doc_id,
                document_name=doc.document_type.name if doc.document_type else doc.file_name,
                application_id=doc.application_id,
                case_reference=application.application_number,
                uploader_id=user_id,
                notify_hr_id=application.assigned_hr_id,
                notify_attorney_id=application.assigned_attorney_id,
            )

    doc_updated = await _load_doc_with_type(db, doc_id)
    return _to_response(doc_updated)


async def get_expected_ocr_slug(db: AsyncSession, doc_id: uuid.UUID) -> Optional[str]:
    """The ONE place that decides what a document is expected to be.
    Pulled straight from DocumentType.ocr_slug via the document's own FK —
    no name matching, no filename guessing. None = no fixed-format
    expectation, so callers must skip the mismatch check entirely."""
    doc = await _load_doc_with_type(db, doc_id)
    if not doc or not doc.document_type:
        return None
    return doc.document_type.ocr_slug

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
    doc = await db_get_by_id(db, Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # 2. Reset any linked task back to pending
    task = await db_get_by_field(db, ApplicationTask, "document_id", doc_id)
    if task:
        await db_update(db, ApplicationTask, task.id, {
            "document_id":  None,
            "is_completed": False,
            "completed_at": None,
            "completed_by": None,
            "modified_by":  user_id,
        })

    # 3. Delete OCR fields — bulk delete, kept raw (db_delete only removes one
    #    row by primary key; a document can have many OCR field rows).
    await db.execute(
        delete(DocumentOCRField).where(DocumentOCRField.document_id == doc_id)
    )

    # 4. Delete physical file from storage (don't block if it fails)
    try:
        await storage.delete_file(doc.file_path)
    except Exception:
        pass

    # 5. Delete document record and commit
    await db_delete(db, Document, doc_id)
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# REUSE — attach an existing Hub document to a new case, WITHOUT re-uploading
# ─────────────────────────────────────────────────────────────────────────────

async def reuse_document_for_case(
    db:                  AsyncSession,
    user_id:             uuid.UUID,
    source_document_id:  uuid.UUID,
    application_id:      uuid.UUID,
) -> DocumentResponse:
    """Attach an existing Hub document to a new case WITHOUT re-uploading —
    duplicates the storage object so the two Document rows are fully
    independent (safe to delete one without breaking the other)."""

    # NOTE: must eager-load document_type here (not db_get_by_id) — this
    # function reads src.document_type.name further down for the task match,
    # and lazy-loading a relationship outside an explicit await on an async
    # engine raises MissingGreenlet.
    src = await _load_doc_with_type(db, source_document_id)
    if not src:
        raise HTTPException(status_code=404, detail="Source document not found.")
    if src.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Duplicate the physical file under a case-scoped key
    safe_name      = os.path.basename(src.file_name)
    storage_prefix = settings.STORAGE_PREFIX
    new_path = f"{storage_prefix}/users/{user_id}/documents/{application_id}/{safe_name}"
    await storage.copy_file(src.file_path, new_path)

    new_doc = Document(
        user_id            = user_id,
        application_id     = application_id,
        document_type_id   = src.document_type_id,
        file_name          = src.file_name,
        file_path          = new_path,
        file_size_kb       = src.file_size_kb,
        file_format        = src.file_format,
        total_pages        = src.total_pages,
        status             = "uploaded",       # fresh — needs this case's own review
        ocr_status         = src.ocr_status,    # carry over — no need to redo OCR
        ocr_confidence     = src.ocr_confidence,
        version            = 1,
        parent_document_id = src.id,            # traceability back to the Hub original
        is_draft           = False,
        created_by         = user_id,
    )
    new_doc = await db_create(db, new_doc)

    # Copy over confirmed OCR fields too, so the student doesn't redo review.
    # limit set generously above db_list's default (50) — a document could
    # plausibly have more than 50 extracted fields on a dense multi-page form.
    src_fields = await db_list(
        db, DocumentOCRField,
        filters=[DocumentOCRField.document_id == src.id],
        limit=500,
    )
    for f in src_fields:
        await db_create(db, DocumentOCRField(
            document_id      = new_doc.id,
            field_name       = f.field_name,
            extracted_value  = f.extracted_value,
            confidence_score = f.confidence_score,
            is_confirmed     = f.is_confirmed,
            needs_review     = f.needs_review,
            created_by       = user_id,
        ))

    # Link to the matching task, same as a fresh upload
    src_type_name = src.document_type.name if src.document_type else ""
    task = await _find_task(
        db,
        application_id=application_id,
        task_name_like=src_type_name,
        only_incomplete=True,
    )
    if task:
        await db_update(db, ApplicationTask, task.id, {
            "document_id": new_doc.id,
            "modified_by": user_id,
        })

    doc_with_type = await _load_doc_with_type(db, new_doc.id)
    return _to_response(doc_with_type)


# ─────────────────────────────────────────────────────────────────────────────
# HUB — all of a user's documents across every case, for the reuse picker
# ─────────────────────────────────────────────────────────────────────────────

async def list_hub_documents(
    db:      AsyncSession,
    user_id: uuid.UUID,
    search:  Optional[str] = None,
) -> DocumentListResponse:
    """All of a user's documents across every case — the picker's 'From Hub' tab.
    Scoped to user_id — a student only ever sees their own uploads, never
    another user's documents, regardless of search term.
    Kept as a raw query (not db_list) — needs joinedload(document_type) both
    for _to_response() and for the search-by-type-name filter below."""
    stmt = (
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    docs = _collapse_hub_families(docs)
    if search:
        s = search.lower()
        docs = [d for d in docs if s in (d.file_name or "").lower()
                or s in (d.document_type.name.lower() if d.document_type else "")]

    return DocumentListResponse(items=[_to_response(d) for d in docs], total=len(docs))