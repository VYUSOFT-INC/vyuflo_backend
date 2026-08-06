# app/routes/hr_document_request_routes.py
#
# "Request from Employee" — the real implementation behind the button on
# the Documents & Checklist screen.
#
# Mount in main.py ALONGSIDE hr_document_router:
#   from app.routes.hr_document_request_routes import hr_document_request_router
#   app.include_router(hr_document_request_router, prefix="/api/v1/hr", tags=["HR Document Requests"])
#
# Endpoints:
#   POST   /api/v1/hr/cases/{application_id}/documents/requests
#   GET    /api/v1/hr/cases/{application_id}/documents/requests
#   PATCH  /api/v1/hr/documents/requests/{request_id}/cancel

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.hr.hr_document_request_schemas import (
    DocumentRequestCreate,
    DocumentRequestListResponse,
    DocumentRequestResponse,
)
from app.services.hr.hr_document_request_service import (
    hr_cancel_document_request,
    hr_create_document_request,
    hr_list_document_requests,
)

hr_document_request_router = APIRouter()


@hr_document_request_router.post(
    "/cases/{application_id}/documents/requests",
    response_model=DocumentRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="HR: Request a document from the employee",
    description="""
Backs the "Request from Employee" button on the Documents & Checklist screen.

Creates a `DocumentRequest` row (trackable pending → fulfilled/cancelled) and
sends the employee a `document_requested` notification. No document needs to
exist yet — this is for asking for something that hasn't been uploaded, or
that needs to be replaced.
    """,
)
async def api_hr_create_document_request(
    application_id: uuid.UUID,
    payload:        DocumentRequestCreate,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> DocumentRequestResponse:
    return await hr_create_document_request(db, application_id, current_user.user_id, payload)


@hr_document_request_router.get(
    "/cases/{application_id}/documents/requests",
    response_model=DocumentRequestListResponse,
    summary="HR: List document requests sent for this case",
)
async def api_hr_list_document_requests(
    application_id: uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> DocumentRequestListResponse:
    return await hr_list_document_requests(db, application_id, current_user.user_id)


@hr_document_request_router.patch(
    "/documents/requests/{request_id}/cancel",
    response_model=DocumentRequestResponse,
    summary="HR: Cancel a pending document request",
)
async def api_hr_cancel_document_request(
    request_id: uuid.UUID,
    db:         AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> DocumentRequestResponse:
    return await hr_cancel_document_request(db, request_id, current_user.user_id)
