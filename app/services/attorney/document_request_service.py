import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.visamodels import (
    Application, DocumentRequest, Notification, DocumentActivity,
)
from app.schemas.attorney.document_request import (
    DocumentRequestCreate, DocumentRequestResponse, DocumentRequestListResponse,
    HRReviewDocumentRequest, HRReviewDecision,
)
from app.services.employee.services import db_create, db_update
from app.services.attorney.case_access import get_case_role


# =============================================================================
# 1. CREATE A REQUEST
#
# HR-relay rule: if the ATTORNEY creates this, it's staged in
# 'pending_hr_approval' and the employee is NOT notified yet — HR has to
# approve it first (see hr_review_document_request below). If HR (or an
# app_admin) creates it, it goes straight to 'pending' and the employee is
# notified immediately, same as before — HR is already the checkpoint, so
# there's nothing to relay it through.
# =============================================================================

async def create_document_request(
    db: AsyncSession, actor_id: uuid.UUID, payload: DocumentRequestCreate
) -> DocumentRequestResponse:
    result = await db.execute(select(Application).where(Application.id == payload.application_id))
    application = result.scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    role = await get_case_role(db, actor_id, application)
    if role is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this case.")

    is_attorney_originated = (role == "attorney")
    initial_status = "pending_hr_approval" if is_attorney_originated else "pending"

    request = DocumentRequest(
        application_id = payload.application_id,
        requested_by   = actor_id,
        requested_from = application.user_id,
        document_name  = payload.document_name,
        details        = payload.details,
        priority       = payload.priority,
        due_date       = payload.due_date,
        status         = initial_status,
        created_by     = actor_id,
    )
    request = await db_create(db, request)

    if is_attorney_originated:
        # Notify HR that something needs their review — NOT the employee.
        if application.assigned_hr_id:
            _notif = await db_create(db, Notification(
                user_id            = application.assigned_hr_id,
                notification_type  = "document_request_needs_hr_review",
                category           = "case_update",
                priority           = "high" if payload.priority in ("high", "urgent") else "medium",
                title              = f"Attorney requested: {payload.document_name}",
                body               = f"Review before it's sent to the employee. {payload.details}",
                application_id     = application.id,
                actor_id           = actor_id,
                created_by         = actor_id,
            ))
            from app.services.admin.admin_notification_fanout import fan_out_notification_to_admins
            await fan_out_notification_to_admins(db, _notif)
    else:
        # HR (or admin) — goes straight to the employee, as before.
        _notif = await db_create(db, Notification(
            user_id            = application.user_id,
            notification_type  = "document_requested",
            category           = "case_update",
            priority           = "high" if payload.priority in ("high", "urgent") else "medium",
            title              = f"Document requested: {payload.document_name}",
            body               = payload.details,
            application_id     = application.id,
            actor_id           = actor_id,
            created_by         = actor_id,
        ))
        from app.services.admin.admin_notification_fanout import fan_out_notification_to_admins
        await fan_out_notification_to_admins(db, _notif)

    return DocumentRequestResponse.model_validate(request)

# =============================================================================
# 2. HR REVIEWS AN ATTORNEY-ORIGINATED REQUEST
# =============================================================================

async def hr_review_document_request(
    db: AsyncSession,
    hr_user_id: uuid.UUID,
    request_id: uuid.UUID,
    payload: HRReviewDocumentRequest,
) -> DocumentRequestResponse:
    result = await db.execute(select(DocumentRequest).where(DocumentRequest.id == request_id))
    request = result.scalars().first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found.")

    result = await db.execute(select(Application).where(Application.id == request.application_id))
    application = result.scalars().first()
    if not application or application.assigned_hr_id != hr_user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this case.")

    if request.status != "pending_hr_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Request is '{request.status}', not 'pending_hr_approval' — nothing to review.",
        )

    if payload.decision == HRReviewDecision.decline and not payload.reason:
        raise HTTPException(status_code=422, detail="reason is required when declining a request.")

    update_data = {
        "hr_reviewed_by": hr_user_id,
        "hr_reviewed_at": datetime.now(timezone.utc),
        "modified_by":    hr_user_id,
    }

    if payload.decision == HRReviewDecision.approve:
        update_data["status"] = "pending"
        await db_update(db, DocumentRequest, request_id, update_data)

        # NOW notify the employee — this is the moment they first learn about it.
# NOW notify the employee — this is the moment they first learn about it.
        _notif = await db_create(db, Notification(
            user_id            = application.user_id,
            notification_type  = "document_requested",
            category           = "case_update",
            priority           = "high" if request.priority in ("high", "urgent") else "medium",
            title              = f"Document requested: {request.document_name}",
            body               = request.details,
            application_id     = application.id,
            actor_id           = hr_user_id,
            created_by         = hr_user_id,
        ))
        from app.services.admin.admin_notification_fanout import fan_out_notification_to_admins
        await fan_out_notification_to_admins(db, _notif)
    else:
        update_data["status"] = "declined"
        update_data["hr_decision_reason"] = payload.reason
        await db_update(db, DocumentRequest, request_id, update_data)

        # Notify the attorney who asked — the employee never knew, so they
        # don't get told anything either.
        _notif = await db_create(db, Notification(
            user_id            = request.requested_by,
            notification_type  = "document_request_declined",
            category           = "case_update",
            priority           = "medium",
            title              = f"HR declined your request: {request.document_name}",
            body               = payload.reason,
            application_id     = application.id,
            actor_id           = hr_user_id,
            created_by         = hr_user_id,
        ))
        from app.services.admin.admin_notification_fanout import fan_out_notification_to_admins
        await fan_out_notification_to_admins(db, _notif)
    result = await db.execute(select(DocumentRequest).where(DocumentRequest.id == request_id))
    return DocumentRequestResponse.model_validate(result.scalars().first())


# =============================================================================
# 3. HR'S QUEUE — requests awaiting their review
# =============================================================================

async def hr_list_pending_request_approvals(
    db: AsyncSession, hr_user_id: uuid.UUID
) -> DocumentRequestListResponse:
    result = await db.execute(
        select(DocumentRequest)
        .join(Application, DocumentRequest.application_id == Application.id)
        .where(
            Application.assigned_hr_id == hr_user_id,
            DocumentRequest.status == "pending_hr_approval",
        )
        .order_by(DocumentRequest.created_at.asc())
    )
    items = result.scalars().all()
    return DocumentRequestListResponse(
        items=[DocumentRequestResponse.model_validate(i) for i in items],
        total=len(items),
    )


# =============================================================================
# 4. ATTORNEY/HR VIEWS ALL REQUESTS FOR A CASE (unchanged, now enum-aware)
# =============================================================================

async def list_document_requests_for_application(
    db: AsyncSession, actor_id: uuid.UUID, application_id: uuid.UUID
) -> DocumentRequestListResponse:
    result = await db.execute(select(Application).where(Application.id == application_id))
    application = result.scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    role = await get_case_role(db, actor_id, application)
    if role is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this case.")

    result = await db.execute(
        select(DocumentRequest)
        .where(DocumentRequest.application_id == application_id)
        .order_by(DocumentRequest.created_at.desc())
    )
    items = result.scalars().all()
    return DocumentRequestListResponse(
        items=[DocumentRequestResponse.model_validate(i) for i in items],
        total=len(items),
    )


# =============================================================================
# 5. CLIENT VIEWS THEIR OWN PENDING REQUESTS
#
# Unaffected by the relay — this already filters on status == 'pending',
# which now naturally excludes 'pending_hr_approval' and 'declined' rows,
# so the employee still never sees an attorney's request until HR approves it.
# =============================================================================

async def list_my_pending_requests(
    db: AsyncSession, client_id: uuid.UUID
) -> DocumentRequestListResponse:
    result = await db.execute(
        select(DocumentRequest)
        .where(DocumentRequest.requested_from == client_id, DocumentRequest.status == "pending")
        .order_by(DocumentRequest.created_at.desc())
    )
    items = result.scalars().all()
    return DocumentRequestListResponse(
        items=[DocumentRequestResponse.model_validate(i) for i in items],
        total=len(items),
    )


# =============================================================================
# 6. ATTORNEY/HR CANCELS A REQUEST — now allowed from either pending state
# =============================================================================

async def cancel_document_request(
    db: AsyncSession, actor_id: uuid.UUID, request_id: uuid.UUID
) -> dict:
    result = await db.execute(select(DocumentRequest).where(DocumentRequest.id == request_id))
    request = result.scalars().first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found.")

    result = await db.execute(select(Application).where(Application.id == request.application_id))
    application = result.scalars().first()
    role = await get_case_role(db, actor_id, application)
    if role is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this case.")

    if request.status not in ("pending", "pending_hr_approval"):
        raise HTTPException(
            status_code=409,
            detail="Only pending requests (including ones awaiting HR review) can be cancelled.",
        )

    await db_update(db, DocumentRequest, request_id, {"status": "cancelled", "modified_by": actor_id})
    return {"detail": "Request cancelled.", "request_id": str(request_id)}


# =============================================================================
# 7. CALLED INTERNALLY WHEN THE CLIENT UPLOADS THE REQUESTED DOCUMENT
#
# This function already existed but was never called from anywhere — the
# request would sit at 'pending' forever even after the employee uploaded
# the matching document. It's now actually wired in from
# document_service.upload_document() (see that file's matching logic).
# =============================================================================

async def fulfill_document_request(
    db: AsyncSession, request_id: uuid.UUID, document_id: uuid.UUID, client_id: uuid.UUID
) -> None:
    result = await db.execute(select(DocumentRequest).where(DocumentRequest.id == request_id))
    request = result.scalars().first()
    if not request:
        raise HTTPException(status_code=404, detail="Document request not found.")
    if request.requested_from != client_id:
        raise HTTPException(status_code=403, detail="This request does not belong to you.")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="This request has already been resolved.")

    await db_update(db, DocumentRequest, request_id, {
        "status":       "fulfilled",
        "document_id":  document_id,
        "fulfilled_at": datetime.now(timezone.utc),
        "modified_by":  client_id,
    })

    await db_create(db, DocumentActivity(
        document_id = document_id,
        action      = "document_requested",
        actor_id    = client_id,
        actor_type  = "user",
        note        = "Uploaded to fulfill a document request.",
        created_by  = client_id,
    ))

# Notify whoever originally asked (attorney or HR — 'requested_by' either way)
    _notif = await db_create(db, Notification(
        user_id            = request.requested_by,
        notification_type  = "document_request_fulfilled",
        category           = "case_update",
        priority           = "medium",
        title              = f"Client uploaded: {request.document_name}",
        body               = "The requested document has been uploaded and is ready for your review.",
        application_id     = request.application_id,
        document_id        = document_id,
        actor_id           = client_id,
        created_by         = client_id,
    ))
    from app.services.admin.admin_notification_fanout import fan_out_notification_to_admins
    await fan_out_notification_to_admins(db, _notif)