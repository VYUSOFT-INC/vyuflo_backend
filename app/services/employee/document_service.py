# app/services/employee/document_service.py
#
# CHANGED: reupload_expired_document() no longer requires the document to
# already be "expired" — replacing a document proactively (before it
# expires) is normal, healthy behavior and should never be blocked. The old
# document is now marked "superseded" (not left as "verified"/"pending_review"
# forever, which would be misleading once a newer version exists) instead of
# being silently untouched. Function name kept as reupload_expired_document
# for API/route compatibility, even though it now handles both cases.
#
# REQUIRES a DB migration:
#   ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'superseded';
# and the same value added to Document.status's Enum(...) list in models.py.
#
# CLEANED UP: this file previously had TWO definitions of
# reuse_document_for_case() — an old one (name-matching guess) followed by
# the fixed one (task_id-aware). Python silently kept only the second
# (later definitions overwrite earlier ones with the same name in a
# module), so this was never actually the cause of the task_id fix not
# taking effect — but it was confusing and risky to leave two copies
# sitting in the same file. Only one definition remains now.
#
# CLEANED UP (again): removed a large commented-out duplicate of this
# entire file that had accumulated at the top from earlier edit passes.
#
# FIXED (reuse_document_for_case): the destination storage path was built
# only from user_id + application_id + the ORIGINAL filename — so reusing
# the same Hub document (or any document sharing that filename) into the
# same application a second time computed the exact same S3 key as an
# earlier reuse, and the copy_file() call failed with
# botocore.errorfactory.InvalidRequest ("copy request is illegal because
# it is trying to copy an object to itself"). Now prefixes the destination
# key with a fresh uuid4() so every reuse gets a guaranteed-unique path,
# regardless of how many times the same filename gets reused.
#
# FIXED (upload_document — task linking): previously always guessed the
# target task by matching `document_type` (a free-text string, often
# "unclassified" from generic Hub uploads with no task context) against
# task names via ilike(). This is the exact same class of bug that
# reuse_document_for_case() had and was fixed for below — when the caller
# already KNOWS which task an upload is for, it should say so directly via
# task_id instead of making the backend guess from a label that may not
# match anything. Now accepts an optional task_id and prefers it when
# given (with the same application_id ownership guard used in reuse);
# falls back to the old name-matching guess only when no task_id is
# provided at all (e.g. a genuinely standalone/personal Hub upload).

import uuid
import os
from datetime import datetime, timezone
from typing import Optional
from app.core.config import settings
from app.services.employee import storage
from fastapi import HTTPException, UploadFile, status
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

def _to_response(doc: Document, in_use: bool = False) -> DocumentResponse:
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
        in_use           = in_use,
        activates_on     = doc.activates_on,
    )


async def _load_doc_with_type(db: AsyncSession, doc_id: uuid.UUID) -> Optional[Document]:
    """Reload a Document with its document_type relationship."""
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
    """Shared task lookup — wraps db_list so every call site builds its
    filter list the same way instead of hand-rolling a fresh select() each time."""
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
    """One card per "document lineage" in the Hub view — with one exception.

    parent_document_id is used by TWO different flows:

      • reuse_document_for_case() copies a Hub original into a new
        case-scoped row (copy.parent_document_id -> original). This is
        genuine duplication of identical content across cases, so the COPY
        stays hidden here; the ORIGINAL is the one visible card.

      • reupload_expired_document() replaces an old version with a new one
        (new.parent_document_id -> old). Unlike reuse, BOTH versions are
        shown here — the person should be able to see what changed and
        when, not just the current version with the old one silently gone.

    FIXED: a replacement whose old document is still valid (activates_on
    set, waiting for the actual expiry date — see reupload_expired_document)
    has a parent that is deliberately NOT YET "superseded". The original
    version of this function only ever showed a replacement when its
    parent's status was already "superseded", so during the entire waiting
    window the new document was wrongly classified as an "ordinary
    reuse-copy of a still-active original" and hidden from the Hub
    completely. Now also checks activates_on on the document itself — any
    document that's part of a supersede chain (whether already handed off,
    or still waiting to be) is always shown.
    """
    ids   = {d.id for d in docs}
    by_id = {d.id: d for d in docs}

    visible: list[Document] = []
    for d in docs:
        if d.status == "superseded":
            visible.append(d)
            continue

        if d.parent_document_id in ids:
            parent = by_id[d.parent_document_id]
            if parent.status == "superseded" or d.activates_on is not None:
                visible.append(d)
            continue

        visible.append(d)

    return visible


async def _check_document_in_use(db: AsyncSession, document_id: uuid.UUID) -> Optional[str]:
    """
    Returns a human-readable reason if the document can't be deleted, else None.
    Two conditions:
      1. Another document reuses/replaces this one (parent_document_id points here) —
         this also correctly blocks deleting a "superseded" original, since the
         document that replaced it always has parent_document_id set to it.
      2. This document is attached to an ApplicationTask that's already completed.
    """
    reused = await db.execute(
        select(Document.id).where(Document.parent_document_id == document_id)
    )
    if reused.scalars().first():
        return (
            "A newer version of this document exists and can't be deleted here. "
            "Manage it from the newer version instead."
        )

    completed_task = await db.execute(
        select(ApplicationTask.id).where(
            ApplicationTask.document_id == document_id,
            ApplicationTask.is_completed == True,  # noqa: E712
        )
    )
    if completed_task.scalars().first():
        return (
            "This document has already been confirmed for a case and can't be "
            "deleted from the Hub."
        )

    return None


async def _get_in_use_document_ids(db: AsyncSession, document_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Batch version of _check_document_in_use, for list endpoints."""
    if not document_ids:
        return set()

    reused = await db.execute(
        select(Document.parent_document_id).where(
            Document.parent_document_id.in_(document_ids)
        )
    )
    reused_ids = {row[0] for row in reused.all() if row[0] is not None}

    completed = await db.execute(
        select(ApplicationTask.document_id).where(
            ApplicationTask.document_id.in_(document_ids),
            ApplicationTask.is_completed == True,  # noqa: E712
        )
    )
    completed_ids = {row[0] for row in completed.all() if row[0] is not None}

    return reused_ids | completed_ids


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

    if application_id is None:
        docs = _collapse_hub_families(docs)

    in_use_ids = await _get_in_use_document_ids(db, [d.id for d in docs])

    return DocumentListResponse(
        items=[_to_response(d, in_use=(d.id in in_use_ids)) for d in docs],
        total=len(docs),
    )


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

    in_use = (await _check_document_in_use(db, document_id)) is not None
    return _to_response(doc, in_use=in_use)


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
    perms = await get_effective_permissions(user_id, db)

    if "documents.view_all" in perms:
        return True
    if "documents.view_own" in perms and doc.user_id == user_id:
        return True
    if "documents.view_team" in perms:
        if await _is_my_employee(db, hr_user_id=user_id, employee_id=doc.user_id):
            return True
        if doc.application_id and await _is_assigned_hr(db, doc.application_id, user_id):
            return True
    if "documents.view_assigned" in perms and doc.application_id:
        if await _is_assigned_attorney(db, doc.application_id, user_id):
            return True
    return False


async def _is_my_employee(db: AsyncSession, hr_user_id: uuid.UUID, employee_id: uuid.UUID) -> bool:
    rows = await db_list(db, EmployerEmployee, filters=[
        EmployerEmployee.employer_id == hr_user_id,
        EmployerEmployee.employee_id == employee_id,
        EmployerEmployee.is_active == True,  # noqa: E712
    ], limit=1)
    return len(rows) > 0


async def _is_assigned_hr(db: AsyncSession, application_id: uuid.UUID, viewer_id: uuid.UUID) -> bool:
    app = await db_get_by_id(db, Application, application_id)
    return app is not None and app.assigned_hr_id == viewer_id


async def _is_assigned_attorney(db: AsyncSession, application_id: uuid.UUID, viewer_id: uuid.UUID) -> bool:
    app = await db_get_by_id(db, Application, application_id)
    return app is not None and app.assigned_attorney_id == viewer_id


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

async def upload_document(
    db:             AsyncSession,
    user_id:        uuid.UUID,
    application_id: Optional[uuid.UUID],
    document_type:  str,
    category:       str,
    file:           UploadFile,
    custom_name:    Optional[str] = None,
    task_id:        Optional[uuid.UUID] = None,   # ← NEW
) -> DocumentResponse:

    doc_type = await db_get_by_field(db, DocumentType, "name", document_type)
    if not doc_type:
        doc_type = DocumentType(
            name        = document_type,
            category    = category,
            description = f"Auto-created: {document_type}",
            created_by  = user_id,
        )
        doc_type = await db_create(db, doc_type)

    content      = await file.read()
    file_size_kb = len(content) // 1024
    ext          = (file.filename or "file").rsplit(".", 1)[-1].lower()
    file_format  = ext if ext in ("pdf", "jpg", "png", "docx", "jpeg", "gif") else "pdf"
    if file_format == "jpeg":
        file_format = "jpg"

    safe_name    = os.path.basename(file.filename or f"document.{file_format}")
    storage_prefix = settings.STORAGE_PREFIX
    storage_path = f"{storage_prefix}/users/{user_id}/documents/{document_type}/{safe_name}"
    await storage.upload_file(
        content,
        storage_path,
        file.content_type or "application/octet-stream",
    )

    display_name = file.filename
    if custom_name and custom_name.strip():
        clean = custom_name.strip()
        display_name = clean if "." in clean else f"{clean}.{file_format}"

    doc = Document(
        user_id          = user_id,
        application_id   = application_id,
        document_type_id = doc_type.id,
        file_name        = display_name,
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

    # ── TASK LINKING ──────────────────────────────────────────────────────
    # FIXED: task_id (when the caller already knows which task this upload
    # satisfies) is now preferred over guessing from document_type text.
    # Same ownership guard as reuse_document_for_case: a task_id belonging
    # to a different application is never trusted.
    if application_id:
        task = None
        if task_id:
            task = await db_get_by_id(db, ApplicationTask, task_id)
            if task and task.application_id != application_id:
                task = None
        else:
            # No task_id given at all — fall back to the old best-effort
            # guess. This path still silently fails to link when
            # document_type doesn't resemble any task name (e.g. a generic
            # "unclassified" upload) — that's expected/acceptable for a
            # genuinely standalone document with no task context.
            task = await _find_task(
                db,
                application_id=application_id,
                task_name_like=document_type,
                only_incomplete=True,
            )

        if task:
            await db_update(db, ApplicationTask, task.id, {
                "document_id": doc.id,
                "modified_by": user_id,
            })

    doc_with_type = await _load_doc_with_type(db, doc.id)
    return _to_response(doc_with_type)


# ─────────────────────────────────────────────────────────────────────────────
# RENAME
# ─────────────────────────────────────────────────────────────────────────────

async def rename_document(
    db:       AsyncSession,
    doc_id:   uuid.UUID,
    user_id:  uuid.UUID,
    new_name: str,
) -> DocumentResponse:
    doc = await _load_doc_with_type(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    clean = (new_name or "").strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    ext = f".{doc.file_format}" if doc.file_format else ""
    if "." not in clean:
        clean = f"{clean}{ext}"

    await db_update(db, Document, doc_id, {
        "file_name":   clean,
        "modified_by": user_id,
    })

    doc_with_type = await _load_doc_with_type(db, doc_id)
    return _to_response(doc_with_type)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIRM OCR
# ─────────────────────────────────────────────────────────────────────────────

async def confirm_document_ocr(
    db:      AsyncSession,
    doc_id:  uuid.UUID,
    user_id: uuid.UUID,
) -> DocumentResponse:

    doc = await _load_doc_with_type(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    await db_update(db, Document, doc_id, {
        "ocr_status":  "confirmed",
        "status":      "pending_review",
        "modified_by": user_id,
    })

    task = await _find_task(db, document_id=doc_id, only_incomplete=True)
    if task:
        await db_update(db, ApplicationTask, task.id, {
            "is_completed": True,
            "completed_at": datetime.now(timezone.utc),
            "completed_by": user_id,
            "modified_by":  user_id,
        })

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
    doc = await _load_doc_with_type(db, doc_id)
    if not doc or not doc.document_type:
        return None
    return doc.document_type.ocr_slug


# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────────────────────────────────────

async def delete_document(
    db:      AsyncSession,
    doc_id:  uuid.UUID,
    user_id: uuid.UUID,
) -> None:

    doc = await db_get_by_id(db, Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    block_reason = await _check_document_in_use(db, doc_id)
    if block_reason:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=block_reason)

    task = await db_get_by_field(db, ApplicationTask, "document_id", doc_id)
    if task:
        await db_update(db, ApplicationTask, task.id, {
            "document_id":  None,
            "is_completed": False,
            "completed_at": None,
            "completed_by": None,
            "modified_by":  user_id,
        })

    await db.execute(
        delete(DocumentOCRField).where(DocumentOCRField.document_id == doc_id)
    )

    try:
        await storage.delete_file(doc.file_path)
    except Exception:
        pass

    deleted = await db_delete(db, Document, doc_id)
    if not deleted:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Delete did not affect any rows — document may already be gone or the ID doesn't match.",
        )

    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# REUSE — attach an existing Hub document to a new case, WITHOUT re-uploading
#
# FIXED (task linking): previously guessed the target task by matching the
# SOURCE document's own type name against task names — but a Hub document
# is routinely reused for a DIFFERENT requirement than the one it was
# originally categorized under (e.g. reusing a resume categorized as
# "Resume / CV" for an "Offer Letter" task), so that guess frequently
# matched nothing and silently left the task unlinked/incomplete even
# though the file itself uploaded fine. The frontend already knows exactly
# which task the person clicked "From Hub" on — use that directly when
# given, falling back to the old name-guessing only if no task_id was
# provided (e.g. a future caller with no specific task context).
#
# FIXED (storage collision): the destination storage path used to be built
# only from user_id + application_id + the ORIGINAL filename, so reusing
# the same document (or any document sharing that filename) into the same
# application a second time computed the identical S3 key as an earlier
# reuse, and copy_file() failed with botocore's "copy request is illegal
# because it is trying to copy an object to itself." Now prefixes the
# destination key with a fresh uuid4() so every reuse gets a
# guaranteed-unique path.
#
# Debug prints (🔎) are intentionally left in while this flow is still
# being verified end-to-end — safe to remove once confirmed stable.
# ─────────────────────────────────────────────────────────────────────────────

async def reuse_document_for_case(
    db:                  AsyncSession,
    user_id:             uuid.UUID,
    source_document_id:  uuid.UUID,
    application_id:      uuid.UUID,
    task_id:             Optional[uuid.UUID] = None,
) -> DocumentResponse:
    print(f"🔎 REUSE CALLED — source_document_id={source_document_id} application_id={application_id} task_id={task_id!r}")

    src = await _load_doc_with_type(db, source_document_id)
    if not src:
        raise HTTPException(status_code=404, detail="Source document not found.")
    if src.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    safe_name      = os.path.basename(src.file_name)
    storage_prefix = settings.STORAGE_PREFIX
    new_doc_id     = uuid.uuid4()
    new_path = f"{storage_prefix}/users/{user_id}/documents/{application_id}/{new_doc_id}_{safe_name}"
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
        status             = "uploaded",
        ocr_status         = src.ocr_status,
        ocr_confidence     = src.ocr_confidence,
        version            = 1,
        parent_document_id = src.id,
        is_draft           = False,
        created_by         = user_id,
    )
    new_doc = await db_create(db, new_doc)
    print(f"🔎 NEW DOC CREATED — new_doc.id={new_doc.id}")

    src_fields = await db_list(
        db, DocumentOCRField,
        filters=[DocumentOCRField.document_id == src.id],
        limit=500,
    )
    print(f"🔎 SRC FIELDS FOUND — count={len(src_fields)}")
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

    if task_id:
        print(f"🔎 TASK_ID BRANCH — looking up task_id={task_id}")
        task = await db_get_by_id(db, ApplicationTask, task_id)
        print(f"🔎 TASK LOOKUP RESULT — task={task!r}")
        if task:
            print(f"🔎 TASK.application_id={task.application_id!r} vs param application_id={application_id!r} equal={task.application_id == application_id}")
        if task and task.application_id != application_id:
            print("🔎 GUARD TRIPPED — application_id mismatch, discarding task")
            task = None
    else:
        print("🔎 NO TASK_ID — falling back to name-matching")
        src_type_name = src.document_type.name if src.document_type else ""
        task = await _find_task(
            db,
            application_id=application_id,
            task_name_like=src_type_name,
            only_incomplete=True,
        )
        print(f"🔎 NAME-MATCH RESULT — task={task!r}")

    if task:
        print(f"🔎 UPDATING TASK — task.id={task.id} -> document_id={new_doc.id}")
        result = await db_update(db, ApplicationTask, task.id, {
            "document_id": new_doc.id,
            "modified_by": user_id,
        })
        print(f"🔎 db_update RETURNED — {result!r}")
    else:
        print("🔎 NO TASK TO UPDATE — task was None")

    doc_with_type = await _load_doc_with_type(db, new_doc.id)
    return _to_response(doc_with_type)


# ─────────────────────────────────────────────────────────────────────────────
# REPLACE / RE-UPLOAD — swap in a new version of a document, expired or not.
# ─────────────────────────────────────────────────────────────────────────────

async def reupload_expired_document(
    db:             AsyncSession,
    old_doc_id:     uuid.UUID,
    user_id:        uuid.UUID,
    file:           UploadFile,
) -> DocumentResponse:
    """
    Replace an existing document with a new version. Works whether the old
    document has already expired or is being proactively renewed early.
    Old document is never deleted — kept as history, status set to
    "superseded", chained via parent_document_id.
    """
    old_doc = await _load_doc_with_type(db, old_doc_id)
    if not old_doc:
        raise HTTPException(status_code=404, detail="Original document not found.")
    if old_doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if old_doc.status == "superseded":
        raise HTTPException(
            status_code=400,
            detail="This document has already been replaced by a newer version.",
        )

    from datetime import date as _date

    content      = await file.read()
    file_size_kb = len(content) // 1024
    ext          = (file.filename or "file").rsplit(".", 1)[-1].lower()
    file_format  = ext if ext in ("pdf", "jpg", "png", "docx", "jpeg", "gif") else "pdf"
    if file_format == "jpeg":
        file_format = "jpg"

    safe_name      = os.path.basename(file.filename or f"document.{file_format}")
    storage_prefix = settings.STORAGE_PREFIX
    storage_path = f"{storage_prefix}/users/{user_id}/documents/{old_doc.document_type_id}/{safe_name}"
    await storage.upload_file(content, storage_path, file.content_type or "application/octet-stream")

    old_still_valid = bool(old_doc.expiry_date) and old_doc.expiry_date >= _date.today()

    new_doc = Document(
        user_id            = user_id,
        application_id     = old_doc.application_id,
        document_type_id   = old_doc.document_type_id,
        file_name          = file.filename,
        file_path          = storage_path,
        file_size_kb       = file_size_kb,
        file_format        = file_format,
        status             = "uploaded",
        ocr_status         = "not_started",
        version            = old_doc.version + 1,
        parent_document_id = old_doc.id,
        activates_on       = old_doc.expiry_date if old_still_valid else None,
        is_draft           = False,
        created_by         = user_id,
    )
    new_doc = await db_create(db, new_doc)

    if old_still_valid:
        pass
    else:
        await db_update(db, Document, old_doc.id, {
            "status":      "superseded",
            "modified_by": user_id,
        })

    task = await db_get_by_field(db, ApplicationTask, "document_id", old_doc_id)
    if task:
        await db_update(db, ApplicationTask, task.id, {
            "document_id":  new_doc.id,
            "is_completed": True,
            "completed_at": datetime.now(timezone.utc),
            "completed_by": user_id,
            "modified_by":  user_id,
        })

    doc_with_type = await _load_doc_with_type(db, new_doc.id)
    return _to_response(doc_with_type)


# ─────────────────────────────────────────────────────────────────────────────
# VERSION HISTORY
# ─────────────────────────────────────────────────────────────────────────────

async def get_document_version_history(
    db:      AsyncSession,
    doc_id:  uuid.UUID,
    user_id: uuid.UUID,
) -> list[dict]:
    """
    GET /documents/:id/versions
    Returns the full replacement chain for a document, oldest first, NOT
    including the document itself.
    """
    doc = await db_get_by_id(db, Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    chain: list[dict] = []
    current = doc
    seen: set[uuid.UUID] = {doc.id}

    while current.parent_document_id and current.parent_document_id not in seen:
        parent = await db_get_by_id(db, Document, current.parent_document_id)
        if not parent:
            break
        chain.append({
            "id":         parent.id,
            "file_name":  parent.file_name,
            "version":    parent.version,
            "status":     parent.status,
            "uploaded_at": parent.created_at,
        })
        seen.add(parent.id)
        current = parent

    return list(reversed(chain))


# ─────────────────────────────────────────────────────────────────────────────
# HUB — all of a user's documents across every case, for the reuse picker
# ─────────────────────────────────────────────────────────────────────────────

async def list_hub_documents(
    db:      AsyncSession,
    user_id: uuid.UUID,
    search:  Optional[str] = None,
) -> DocumentListResponse:
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

    in_use_ids = await _get_in_use_document_ids(db, [d.id for d in docs])

    return DocumentListResponse(
        items=[_to_response(d, in_use=(d.id in in_use_ids)) for d in docs],
        total=len(docs),
    )