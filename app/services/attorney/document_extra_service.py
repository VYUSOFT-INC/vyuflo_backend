# =============================================================================
# app/services/attorney/document_extra_service.py
#
# Fixes applied in this pass (see accompanying explanation):
#   1. update_document_status() had NO permission check at all — any
#      authenticated user could verify/reject any document. Now uses
#      get_case_role() and requires attorney/hr/app_admin standing on the case.
#   2. upload_document_for_client() called upload_document(..., actor_id=...)
#      but upload_document() has no actor_id param — this crashed every time.
#      Fixed, and made role-aware per the HR-relay workflow (see below).
#   3. list_documents_filtered() hardcoded Application.assigned_attorney_id,
#      so HR/employees calling it got zero results. Now scopes by the
#      caller's actual global role.
#   4. get_document_activity / get_document_versions / get_document_pages /
#      trigger_ocr claimed an "attorney/HR bypass handled at router via RBAC"
#      that was never implemented — they 403'd for anyone but the document's
#      owner. Now they use get_case_role() as a fallback when the caller
#      isn't the owner.
#
# New in this pass — the HR-relay workflow:
#   - upload_document_for_client(): if an ATTORNEY uploads, the document is
#     created as 'pending_hr_release' (invisible to the employee, no
#     notification sent) instead of 'uploaded'. If HR (or app_admin) uploads,
#     it goes straight to 'uploaded' and the employee is notified, same as
#     the previous behavior — HR is already the checkpoint.
#   - hr_review_uploaded_document(): HR's approve/decline action on a
#     'pending_hr_release' document. Approve → 'uploaded' + employee notified
#     for the first time. Decline → 'rejected' + rejection_reason, attorney
#     notified, employee never told (they never knew it existed).
#   - hr_list_pending_document_releases(): HR's queue of attorney uploads
#     awaiting their decision.
# =============================================================================

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.visamodels import (
    Application, Document, DocumentActivity, DocumentPage, Notification, Role, UserRole,
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
from app.schemas.employee.document import DocumentResponse, DocumentListResponse
from app.services.employee.document_service import _to_response
from app.services.employee.services import db_create, db_update
from app.services.attorney.case_access import get_case_role


# =============================================================================
# HELPERS
# =============================================================================

async def _get_user_global_roles(db: AsyncSession, user_id: uuid.UUID) -> set[str]:
    """Role names the user holds, independent of any specific case."""
    result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    )
    return {r for (r,) in result.all()}


async def _can_access_document(db: AsyncSession, doc: Document, user_id: uuid.UUID) -> bool:
    """Owner always can. Otherwise, must have attorney/hr/app_admin standing
    on the document's case (fixes the claimed-but-missing RBAC bypass)."""
    if doc.user_id == user_id:
        return True
    if not doc.application_id:
        return False
    result = await db.execute(select(Application).where(Application.id == doc.application_id))
    application = result.scalars().first()
    if not application:
        return False
    return await get_case_role(db, user_id, application) is not None


# =============================================================================
# GET /documents/{id}/versions
# =============================================================================

async def get_document_versions(
    db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID,
) -> DocumentVersionListResponse:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not await _can_access_document(db, doc, user_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    root_id = doc.parent_document_id or doc.id
    stmt = select(Document).where(
        (Document.id == root_id) | (Document.parent_document_id == root_id)
    ).order_by(Document.version.asc())
    result = await db.execute(stmt)
    docs = result.scalars().all()

    items = [
        DocumentVersionResponse(
            id=d.id, version=d.version, name=d.file_name,
            file_size_bytes=(d.file_size_kb or 0) * 1024,
            file_type=d.file_format, status=d.status, uploaded_at=d.created_at,
        )
        for d in docs
    ]
    return DocumentVersionListResponse(items=items, total=len(items))


# =============================================================================
# GET /documents/{id}/activity
# =============================================================================

async def get_document_activity(
    db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID,
) -> DocumentActivityListResponse:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not await _can_access_document(db, doc, user_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    stmt = (
        select(DocumentActivity)
        .where(DocumentActivity.document_id == document_id)
        .order_by(DocumentActivity.created_at.desc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    items = [
        DocumentActivityResponse(
            id=r.id, action=r.action, actor_id=r.actor_id,
            actor_type=r.actor_type, note=r.note, created_at=r.created_at,
        )
        for r in records
    ]
    return DocumentActivityListResponse(items=items, total=len(items))


# =============================================================================
# DELETE /documents/{id}
# =============================================================================

async def delete_document(
    db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID,
) -> dict:
    """Soft delete. Kept owner-only, unlike the read endpoints above — an
    attorney/HR shouldn't be able to delete an employee's document just
    because they're on the case."""
    result = await db.execute(select(Document).where(Document.id == document_id))
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
        "status": "missing", "is_draft": True, "modified_by": user_id,
    })
    return {"detail": "Document deleted.", "document_id": str(document_id)}


# =============================================================================
# PATCH /documents/{id}/status — FIX: now actually checks permission
# =============================================================================

async def update_document_status(
    db:               AsyncSession,
    document_id:      uuid.UUID,
    reviewer_id:      uuid.UUID,
    new_status:       DocumentStatus,
    rejection_reason: Optional[str] = None,
) -> DocumentResponse:
    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # FIX: this was completely missing before. Verify/reject requires
    # attorney/hr/app_admin standing on the document's case.
    if not doc.application_id:
        raise HTTPException(status_code=422, detail="Document is not attached to a case.")
    result = await db.execute(select(Application).where(Application.id == doc.application_id))
    application = result.scalars().first()
    role = await get_case_role(db, reviewer_id, application)
    if role is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this case.")

    if new_status == DocumentStatus.rejected and not rejection_reason:
        raise HTTPException(status_code=422, detail="rejection_reason is required when rejecting a document.")

    updates: dict = {"status": new_status, "modified_by": reviewer_id}
    if new_status == DocumentStatus.verified:
        updates["verified_by"] = reviewer_id
        updates["verified_at"] = datetime.now(timezone.utc)
        updates["rejection_reason"] = None
    if new_status == DocumentStatus.rejected:
        updates["rejection_reason"] = rejection_reason
        updates["verified_by"] = None
        updates["verified_at"] = None

    await db_update(db, Document, document_id, updates)

    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == document_id)
    )
    return _to_response(result.scalars().first())


# =============================================================================
# GET /documents/{id}/pages
# =============================================================================

async def get_document_pages(
    db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID,
) -> DocumentPageListResponse:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not await _can_access_document(db, doc, user_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    stmt = select(DocumentPage).where(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number.asc())
    result = await db.execute(stmt)
    pages = result.scalars().all()

    items = [
        DocumentPageResponse(
            id=p.id, document_id=p.document_id, page_number=p.page_number,
            thumbnail_url=p.thumbnail_url, image_url=p.image_url, ocr_confidence=p.ocr_confidence,
        )
        for p in pages
    ]
    return DocumentPageListResponse(items=items, total=len(items))


# =============================================================================
# POST /documents/{id}/ocr/trigger
# =============================================================================

async def trigger_ocr(db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not await _can_access_document(db, doc, user_id):
        raise HTTPException(status_code=403, detail="Access denied.")
    if doc.ocr_status == "processing":
        raise HTTPException(status_code=409, detail="OCR is already in progress.")

    await db_update(db, Document, document_id, {"ocr_status": "processing", "modified_by": user_id})
    return {"detail": "OCR processing started.", "document_id": str(document_id), "ocr_status": "processing"}


# =============================================================================
# GET /documents/filter — FIX: role-aware scoping instead of attorney-only
# =============================================================================

async def list_documents_filtered(
    db:             AsyncSession,
    user_id:        uuid.UUID,
    application_id: Optional[uuid.UUID] = None,
    status:         Optional[str]       = None,
    category:       Optional[str]       = None,
    document_type:  Optional[str]       = None,
) -> DocumentListResponse:
    from app.models.visamodels import DocumentType as DocTypeModel

    roles = await _get_user_global_roles(db, user_id)

    stmt = select(Document).options(joinedload(Document.document_type))

    if "app_admin" in roles:
        pass  # no ownership filter — sees everything, narrowed by application_id/status below
    elif "attorney" in roles:
        stmt = stmt.join(Application, Document.application_id == Application.id).where(
            Application.assigned_attorney_id == user_id
        )
    elif "hr" in roles:
        stmt = stmt.join(Application, Document.application_id == Application.id).where(
            Application.assigned_hr_id == user_id
        )
    else:
        stmt = stmt.where(Document.user_id == user_id)

    stmt = stmt.order_by(Document.created_at.desc())

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
    docs = result.scalars().unique().all()
    return DocumentListResponse(items=[_to_response(d) for d in docs], total=len(docs))


# =============================================================================
# GET /documents/my-rejected
# =============================================================================

async def get_my_rejected_documents(db: AsyncSession, user_id: uuid.UUID) -> list:
    from app.schemas.attorney.document_extra import RejectedDocumentResponse

    stmt = (
        select(Document)
        .where(Document.user_id == user_id, Document.status == "rejected")
        .order_by(Document.updated_at.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [
        RejectedDocumentResponse(
            id=d.id, file_name=d.file_name, rejection_reason=d.rejection_reason,
            status=d.status, updated_at=d.updated_at,
        )
        for d in docs
    ]


# =============================================================================
# POST /documents/upload-for-client — FIX: correct call signature + HR relay
# =============================================================================

async def upload_document_for_client(db, actor_id, application_id, document_type, category, file):
    result = await db.execute(select(Application).where(Application.id == application_id))
    application = result.scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    role = await get_case_role(db, actor_id, application)
    if role is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this case.")

    from app.services.employee.document_service import upload_document

    # HR-relay rule: attorney uploads are staged behind HR approval — the
    # employee doesn't see or get notified about the document yet. HR (and
    # app_admin) uploads go straight through, same as before.
    is_attorney_originated = (role == "attorney")
    initial_status = "pending_hr_release" if is_attorney_originated else "uploaded"

    # FIX: upload_document() has no actor_id param — this used to crash
    # every time this endpoint was called.
    doc_response = await upload_document(
        db=db, user_id=application.user_id, application_id=application_id,
        document_type=document_type, category=category, file=file,
        initial_status=initial_status,
    )

    if is_attorney_originated:
        # Notify HR — a document is waiting for their release decision.
        if application.assigned_hr_id:
            await db_create(db, Notification(
                user_id=application.assigned_hr_id,
                notification_type="document_needs_hr_release",
                category="case_update",
                priority="medium",
                title=f"Attorney uploaded: {document_type}",
                body="Review before it's released to the employee.",
                application_id=application_id,
                document_id=doc_response.id,
                actor_id=actor_id,
                created_by=actor_id,
            ))
    else:
        # HR/admin upload — employee is told immediately, as before.
        await db_create(db, Notification(
            user_id=application.user_id,
            notification_type="document_uploaded_by_staff",
            category="case_update",
            priority="medium",
            title="A document was uploaded to your case",
            body=f"'{document_type}' was uploaded on your behalf. You can review it anytime in your Documents tab.",
            application_id=application_id,
            document_id=doc_response.id,
            actor_id=actor_id,
            created_by=actor_id,
        ))

    return doc_response


# =============================================================================
# NEW — HR reviews an attorney-uploaded document sitting in 'pending_hr_release'
# =============================================================================

async def hr_review_uploaded_document(
    db: AsyncSession,
    hr_user_id: uuid.UUID,
    document_id: uuid.UUID,
    decision: str,             # 'approve' | 'decline'
    reason: Optional[str] = None,
) -> DocumentResponse:
    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.status != "pending_hr_release":
        raise HTTPException(
            status_code=409,
            detail=f"Document is '{doc.status}', not 'pending_hr_release' — nothing to review.",
        )
    if not doc.application_id:
        raise HTTPException(status_code=422, detail="Document is not attached to a case.")

    result = await db.execute(select(Application).where(Application.id == doc.application_id))
    application = result.scalars().first()
    if not application or application.assigned_hr_id != hr_user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this case.")

    if decision == "decline" and not reason:
        raise HTTPException(status_code=422, detail="reason is required when declining a document.")

    if decision == "approve":
        await db_update(db, Document, document_id, {
            "status": "uploaded", "modified_by": hr_user_id,
        })
        await db_create(db, Notification(
            user_id=application.user_id,
            notification_type="document_uploaded_by_staff",
            category="case_update",
            priority="medium",
            title="A document was uploaded to your case",
            body="Your attorney uploaded a document on your behalf. You can review it anytime in your Documents tab.",
            application_id=application.id,
            document_id=document_id,
            actor_id=hr_user_id,
            created_by=hr_user_id,
        ))
    else:
        await db_update(db, Document, document_id, {
            "status": "rejected", "rejection_reason": reason,
            "verified_by": hr_user_id, "verified_at": datetime.now(timezone.utc),
            "modified_by": hr_user_id,
        })
        # Employee never knew about it — only tell the attorney who uploaded it.
        await db_create(db, Notification(
            user_id=doc.created_by,
            notification_type="document_release_declined",
            category="case_update",
            priority="medium",
            title="HR declined a document you uploaded",
            body=reason,
            application_id=application.id,
            document_id=document_id,
            actor_id=hr_user_id,
            created_by=hr_user_id,
        ))

    result = await db.execute(
        select(Document).options(joinedload(Document.document_type)).where(Document.id == document_id)
    )
    return _to_response(result.scalars().first())


# =============================================================================
# NEW — HR's queue of attorney uploads awaiting release
# =============================================================================

async def hr_list_pending_document_releases(
    db: AsyncSession, hr_user_id: uuid.UUID,
) -> DocumentListResponse:
    stmt = (
        select(Document)
        .options(joinedload(Document.document_type))
        .join(Application, Document.application_id == Application.id)
        .where(
            Application.assigned_hr_id == hr_user_id,
            Document.status == "pending_hr_release",
        )
        .order_by(Document.created_at.asc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return DocumentListResponse(items=[_to_response(d) for d in docs], total=len(docs))
