# app/routes/hr_approval_routes.py
#
# HR Approval Queue router.
# Mount in main.py:
#   from app.routes.hr_approval_routes import hr_approval_router
#   app.include_router(hr_approval_router, prefix="/api/v1/hr", tags=["HR Approvals"])
#
# Endpoints:
#   GET    /api/v1/hr/approvals                              → list approval queue
#   PATCH  /api/v1/hr/approvals/{document_id}/approve        → approve a document
#   PATCH  /api/v1/hr/approvals/{document_id}/request-edits  → request edits
#   POST   /api/v1/hr/approvals/bulk-approve                 → bulk approve

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.hr.hr_approval_schemas import (
    ApprovalListResponse,
    ApprovalItemResponse,
    ApproveDocumentRequest,
    RequestEditsRequest,
    BulkApproveRequest,
)
from app.services.hr.hr_approval_service import (
    hr_list_approvals,
    hr_approve_document,
    hr_request_edits,
    hr_bulk_approve,
)

hr_approval_router = APIRouter()


@hr_approval_router.get(
    "/approvals",
    response_model=ApprovalListResponse,
    summary="List approval queue for HR user's cases",
)
async def api_hr_list_approvals(
    status:     Optional[str] = Query(None),
    priority:   Optional[str] = Query(None),
    doc_type:   Optional[str] = Query(None),
    date_range: Optional[str] = Query("7days"),
    db:         AsyncSession  = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> ApprovalListResponse:
    return await hr_list_approvals(
        db         = db,
        hr_user_id = current_user.user_id,
        status     = status,
        priority   = priority,
        doc_type   = doc_type,
        date_range = date_range,
    )


@hr_approval_router.patch(
    "/approvals/{document_id}/approve",
    response_model=ApprovalItemResponse,
    summary="Approve a document (sets status → verified)",
)
async def api_hr_approve(
    document_id:  uuid.UUID,
    payload:      ApproveDocumentRequest = ApproveDocumentRequest(),
    db:           AsyncSession           = Depends(get_db),
    current_user                         = Depends(get_current_user),
) -> ApprovalItemResponse:
    return await hr_approve_document(
        db          = db,
        hr_user_id  = current_user.user_id,
        document_id = document_id,
        note        = payload.note,
    )


@hr_approval_router.patch(
    "/approvals/{document_id}/request-edits",
    response_model=ApprovalItemResponse,
    summary="Request edits on a document (sets status → rejected with note)",
)
async def api_hr_request_edits(
    document_id:  uuid.UUID,
    payload:      RequestEditsRequest,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> ApprovalItemResponse:
    return await hr_request_edits(
        db          = db,
        hr_user_id  = current_user.user_id,
        document_id = document_id,
        note        = payload.note,
    )


@hr_approval_router.post(
    "/approvals/bulk-approve",
    summary="Bulk approve multiple documents at once",
)
async def api_hr_bulk_approve(
    payload:      BulkApproveRequest,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> dict:
    return await hr_bulk_approve(
        db           = db,
        hr_user_id   = current_user.user_id,
        document_ids = payload.document_ids,
        note         = payload.note,
    )