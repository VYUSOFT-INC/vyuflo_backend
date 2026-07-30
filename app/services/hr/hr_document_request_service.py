# app/services/hr/hr_document_request_service.py
"""
"Request from Employee" — real implementation.

Previously `hr_document_routes.hr_request_document` was a TODO stub that only
wrote a DocumentActivity log line and didn't actually notify anyone. This
service replaces that with the real thing:

  1. A `DocumentRequest` row (visamodels.DocumentRequest — already existed,
     unused until now) — gives HR a trackable pending/fulfilled/cancelled
     request instead of just a log line.
  2. A `Notification` for the employee (notification_type='document_requested')
     — this is what actually surfaces the ask to the employee.

Two entry points share this same logic:
  - hr_create_document_request()      — brand-new request, no document exists
                                         yet (case-level "Request from
                                         Employee" button on the Documents &
                                         Checklist screen).
  - hr_document_routes.hr_request_document() — re-request tied to an EXISTING
                                         document (e.g. asking for a
                                         re-upload after rejection). That
                                         route still logs its own
                                         DocumentActivity row (which requires
                                         a non-null document_id) and then
                                         calls hr_create_document_request()
                                         here so both paths converge on one
                                         DocumentRequest + Notification
                                         implementation.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import Application, DocumentRequest, Notification
from app.schemas.hr.hr_document_request_schemas import (
    DocumentRequestCreate,
    DocumentRequestListResponse,
    DocumentRequestResponse,
)
from app.services.employee.services import db_create, db_update


# =============================================================================
# HELPERS
# =============================================================================

async def _assert_hr_owns_case(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> Application:
    result = await db.execute(select(Application).where(Application.id == application_id))
    app = result.scalars().first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {application_id} not found.",
        )
    if app.assigned_hr_id != hr_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this case.",
        )
    return app


# =============================================================================
# CREATE
# =============================================================================

async def hr_create_document_request(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
    payload: DocumentRequestCreate,
    document_id: Optional[uuid.UUID] = None,   # set only when re-requesting an existing document
) -> DocumentRequestResponse:
    app = await _assert_hr_owns_case(db, application_id, hr_user_id)

    request = DocumentRequest(
        application_id = application_id,
        requested_by   = hr_user_id,
        requested_from = app.user_id,
        document_name  = payload.document_name,
        details        = payload.details,
        priority       = payload.priority.value,
        due_date       = payload.due_date,
        status         = "pending",
        document_id    = document_id,
        created_by     = hr_user_id,
    )
    request = await db_create(db, request)

    notification = Notification(
        user_id            = app.user_id,
        notification_type  = "document_requested",
        category           = "case_update",
        priority           = "high" if payload.priority.value in ("high", "urgent") else "medium",
        title              = f"Document requested: {payload.document_name}",
        body               = payload.details,
        application_id     = application_id,
        document_id        = document_id,
        actor_id           = hr_user_id,
        cta_primary_label  = "Upload document",
        created_by         = hr_user_id,
    )
    await db_create(db, notification)
    from app.services.admin.admin_notification_fanout import fan_out_notification_to_admins
    await fan_out_notification_to_admins(db, notification)

    return DocumentRequestResponse.model_validate(request)


# =============================================================================
# LIST
# =============================================================================

async def hr_list_document_requests(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> DocumentRequestListResponse:
    await _assert_hr_owns_case(db, application_id, hr_user_id)

    result = await db.execute(
        select(DocumentRequest)
        .where(DocumentRequest.application_id == application_id)
        .order_by(DocumentRequest.created_at.desc())
    )
    items = result.scalars().all()
    return DocumentRequestListResponse(
        items=[DocumentRequestResponse.model_validate(r) for r in items],
        total=len(items),
    )


# =============================================================================
# CANCEL
# =============================================================================

async def hr_cancel_document_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> DocumentRequestResponse:
    result = await db.execute(select(DocumentRequest).where(DocumentRequest.id == request_id))
    req = result.scalars().first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document request not found.")

    await _assert_hr_owns_case(db, req.application_id, hr_user_id)

    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be cancelled.",
        )

    await db_update(db, DocumentRequest, request_id, {"status": "cancelled", "modified_by": hr_user_id})

    result = await db.execute(select(DocumentRequest).where(DocumentRequest.id == request_id))
    return DocumentRequestResponse.model_validate(result.scalars().first())
