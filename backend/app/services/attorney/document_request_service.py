import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.visamodels import (
    Application, DocumentRequest, Notification,
    Role, UserRole, DocumentActivity,
)
from app.schemas.attorney.document_request import (
    DocumentRequestCreate, DocumentRequestResponse, DocumentRequestListResponse,
)
from app.services.employee.services import db_create, db_update


async def _is_case_staff(db: AsyncSession, actor_id: uuid.UUID, application: Application) -> bool:
    """Checks the actor is the attorney/HR assigned to this case, or an admin."""
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == actor_id)
    )
    role_names = {r for (r,) in result.all()}

    if "app_admin" in role_names:
        return True
    if "attorney" in role_names and application.assigned_attorney_id == actor_id:
        return True
    if "hr" in role_names and application.assigned_hr_id == actor_id:
        return True
    return False


# ── 1. Attorney creates a request ────────────────────────────────────────────
async def create_document_request(
    db: AsyncSession, actor_id: uuid.UUID, payload: DocumentRequestCreate
) -> DocumentRequestResponse:
    result = await db.execute(select(Application).where(Application.id == payload.application_id))
    application = result.scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    if not await _is_case_staff(db, actor_id, application):
        raise HTTPException(status_code=403, detail="You are not assigned to this case.")

    request = DocumentRequest(
        application_id = payload.application_id,
        requested_by   = actor_id,
        requested_from = application.user_id,
        document_name  = payload.document_name,
        details        = payload.details,
        priority       = payload.priority,
        due_date       = payload.due_date,
        status         = "pending",
        created_by     = actor_id,
    )
    request = await db_create(db, request)

    # Notify the client
    await db_create(db, Notification(
        user_id           = application.user_id,
        notification_type = "document_requested",
        category          = "case_update",
        priority          = "high" if payload.priority in ("high", "urgent") else "medium",
        title             = f"Document requested: {payload.document_name}",
        body              = payload.details,
        application_id    = application.id,
        actor_id          = actor_id,
        created_by        = actor_id,
    ))

    return DocumentRequestResponse.model_validate(request)


# ── 2. Attorney/HR views all requests for a case ─────────────────────────────
async def list_document_requests_for_application(
    db: AsyncSession, actor_id: uuid.UUID, application_id: uuid.UUID
) -> DocumentRequestListResponse:
    result = await db.execute(select(Application).where(Application.id == application_id))
    application = result.scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    if not await _is_case_staff(db, actor_id, application):
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


# ── 3. Client views their own pending requests ───────────────────────────────
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


# ── 4. Attorney/HR cancels a request ─────────────────────────────────────────
async def cancel_document_request(
    db: AsyncSession, actor_id: uuid.UUID, request_id: uuid.UUID
) -> dict:
    result = await db.execute(select(DocumentRequest).where(DocumentRequest.id == request_id))
    request = result.scalars().first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found.")

    result = await db.execute(select(Application).where(Application.id == request.application_id))
    application = result.scalars().first()
    if not await _is_case_staff(db, actor_id, application):
        raise HTTPException(status_code=403, detail="You are not assigned to this case.")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending requests can be cancelled.")

    await db_update(db, DocumentRequest, request_id, {"status": "cancelled", "modified_by": actor_id})
    return {"detail": "Request cancelled.", "request_id": str(request_id)}


# ── 5. Called internally when the client uploads the requested document ─────
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
        note        = "Uploaded to fulfill an attorney's document request.",
        created_by  = client_id,
    ))

    # Notify the attorney back
    await db_create(db, Notification(
        user_id           = request.requested_by,
        notification_type = "document_request_fulfilled",
        category          = "case_update",
        priority          = "medium",
        title             = f"Client uploaded: {request.document_name}",
        body              = "The requested document has been uploaded and is ready for your review.",
        application_id    = request.application_id,
        document_id       = document_id,
        actor_id          = client_id,
        created_by        = client_id,
    ))
