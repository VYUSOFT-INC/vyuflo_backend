# =============================================================================
# app/routers/document_extra.py
#
# Register in main.py alongside your existing router:
#
#   from app.routers.document_extra import document_extra_router
#   app.include_router(document_extra_router, prefix="/api/v1", tags=["Documents"])
#
# Changes in this pass (see accompanying explanation):
#   - PATCH /documents/{id}/status now actually enforces the "Attorney / HR /
#     Admin only" permission the docstring always claimed (was previously
#     wide open to any authenticated user).
#   - NEW: PATCH /documents/requests/{request_id}/hr-review — HR approves or
#     declines an attorney-created document request.
#   - NEW: GET /documents/requests/pending-hr-approval — HR's queue.
#   - NEW: PATCH /documents/{document_id}/hr-review — HR approves or declines
#     an attorney-uploaded-for-client document sitting in 'pending_hr_release'.
#   - NEW: GET /documents/pending-hr-release — HR's queue for that.
# =============================================================================

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user

# Your existing schema — reused directly
from app.schemas.employee.document import DocumentListResponse, DocumentResponse

# New schemas — separate file, no conflict
from app.schemas.attorney.document_extra import (
    DocumentActivityListResponse,
    DocumentPageListResponse,
    DocumentStatusUpdate,
    DocumentVersionListResponse,
    RejectedDocumentListResponse,
    HRReviewUploadedDocument,       # NEW
)

from app.schemas.attorney.document_request import (
    DocumentRequestCreate, DocumentRequestResponse, DocumentRequestListResponse,
    HRReviewDocumentRequest,        # NEW
)
from app.services.attorney.document_request_service import (
    create_document_request, list_document_requests_for_application,
    list_my_pending_requests, cancel_document_request,
    hr_review_document_request, hr_list_pending_request_approvals,   # NEW
)

# Your existing service — reused for get_document_file_url
from app.services.employee.document_service import get_document_file_url

# New service functions — separate file, no conflict
from app.services.attorney.document_extra_service import (
    delete_document,
    get_document_activity,
    get_document_pages,
    get_document_versions,
    get_my_rejected_documents,
    list_documents_filtered,
    trigger_ocr,
    update_document_status,
    upload_document_for_client,
    hr_review_uploaded_document,        # NEW
    hr_list_pending_document_releases,  # NEW
)

document_extra_router = APIRouter()


# ── GET /documents/filter ─────────────────────────────────────────────────────
@document_extra_router.get(
    "/documents/filter",
    response_model=DocumentListResponse,
    summary="List documents with optional filters (status, category, type) — role-scoped",
)
async def api_list_documents_filtered(
    application_id: Optional[uuid.UUID] = Query(None),
    status:         Optional[str]       = Query(None, description="required|uploaded|pending_review|verified|rejected|missing|pending_hr_release"),
    category:       Optional[str]       = Query(None, description="identity|employment|education|legal|personal|other"),
    document_type:  Optional[str]       = Query(None, description="Matches DocumentType.name exactly"),
    db:             AsyncSession        = Depends(get_db),
    current_user                        = Depends(get_current_user),
) -> DocumentListResponse:
    return await list_documents_filtered(
        db=db, user_id=current_user.user_id, application_id=application_id,
        status=status, category=category, document_type=document_type,
    )


# ── GET /documents/my-rejected ───────────────────────────────────────────────
@document_extra_router.get(
    "/documents/my-rejected",
    response_model=RejectedDocumentListResponse,
    summary="Get all rejected documents for the logged-in client (Action Required)",
)
async def api_get_my_rejected_documents(
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> RejectedDocumentListResponse:
    items = await get_my_rejected_documents(db, current_user.user_id)
    return RejectedDocumentListResponse(items=items, total=len(items))


# ── GET /documents/{id}/download ─────────────────────────────────────────────
@document_extra_router.get(
    "/documents/{document_id}/download",
    summary="Force-download document as attachment (not inline)",
)
async def api_download_document(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    doc       = await get_document_file_url(db, document_id, current_user.user_id)
    file_path = f"./{doc['file_path']}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk.")

    fmt = doc["file_format"].lower()
    media_types = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    media_type = media_types.get(fmt, "application/octet-stream")

    return FileResponse(
        path=file_path, media_type=media_type, filename=doc["file_name"],
        headers={"Content-Disposition": f'attachment; filename="{doc["file_name"]}"'},
    )


# ── GET /documents/{id}/versions ─────────────────────────────────────────────
@document_extra_router.get(
    "/documents/{document_id}/versions",
    response_model=DocumentVersionListResponse,
    summary="Get all versions of a document",
)
async def api_get_document_versions(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentVersionListResponse:
    return await get_document_versions(db, document_id, current_user.user_id)


# ── GET /documents/{id}/activity ─────────────────────────────────────────────
@document_extra_router.get(
    "/documents/{document_id}/activity",
    response_model=DocumentActivityListResponse,
    summary="Get audit log for a document",
)
async def api_get_document_activity(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentActivityListResponse:
    return await get_document_activity(db, document_id, current_user.user_id)


# ── DELETE /documents/{id} ───────────────────────────────────────────────────
@document_extra_router.delete(
    "/documents/{document_id}",
    summary="Soft-delete a document (employee can delete own unverified docs)",
)
async def api_delete_document(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> dict:
    return await delete_document(db, document_id, current_user.user_id)


# ── PATCH /documents/{id}/status ─────────────────────────────────────────────
@document_extra_router.patch(
    "/documents/{document_id}/status",
    response_model=DocumentResponse,
    summary="Verify or reject a document — Attorney / HR / Admin only",
    description="FIX: this endpoint now actually enforces that permission — "
                 "previously anyone authenticated could call it.",
)
async def api_update_document_status(
    document_id:  uuid.UUID,
    payload:      DocumentStatusUpdate,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentResponse:
    return await update_document_status(
        db=db, document_id=document_id, reviewer_id=current_user.user_id,
        new_status=payload.status, rejection_reason=payload.rejection_reason,
    )


# ── GET /documents/{id}/pages ────────────────────────────────────────────────
@document_extra_router.get(
    "/documents/{document_id}/pages",
    response_model=DocumentPageListResponse,
    summary="Get ordered page list with thumbnails (OCR page strip)",
)
async def api_get_document_pages(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentPageListResponse:
    return await get_document_pages(db, document_id, current_user.user_id)


# ── POST /documents/{id}/ocr/trigger ─────────────────────────────────────────
@document_extra_router.post(
    "/documents/{document_id}/ocr/trigger",
    summary="Trigger OCR processing for a document",
)
async def api_trigger_ocr(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> dict:
    return await trigger_ocr(db, document_id, current_user.user_id)


# =============================================================================
# DOCUMENT REQUESTS
# =============================================================================

@document_extra_router.post(
    "/documents/requests",
    response_model=DocumentRequestResponse,
    status_code=201,
    summary="Attorney/HR requests an additional document from a client",
    description=(
        "HR-relay rule: if an ATTORNEY creates this, it's staged in "
        "'pending_hr_approval' and the client is NOT notified yet — see "
        "PATCH /documents/requests/{request_id}/hr-review. If HR (or "
        "app_admin) creates it, it goes straight to the client as before."
    ),
)
async def api_create_document_request(
    payload: DocumentRequestCreate,
    db:      AsyncSession = Depends(get_db),
    current_user           = Depends(get_current_user),
) -> DocumentRequestResponse:
    return await create_document_request(db, current_user.user_id, payload)


@document_extra_router.patch(
    "/documents/requests/{request_id}/hr-review",
    response_model=DocumentRequestResponse,
    summary="HR: approve or decline an attorney-created document request",
    description="Only valid while the request is 'pending_hr_approval'. "
                 "`reason` is required when declining.",
)
async def api_hr_review_document_request(
    request_id: uuid.UUID,
    payload:    HRReviewDocumentRequest,
    db:         AsyncSession = Depends(get_db),
    current_user             = Depends(get_current_user),
) -> DocumentRequestResponse:
    return await hr_review_document_request(db, current_user.user_id, request_id, payload)


@document_extra_router.get(
    "/documents/requests/pending-hr-approval",
    response_model=DocumentRequestListResponse,
    summary="HR: queue of attorney-created requests awaiting my review",
)
async def api_hr_list_pending_request_approvals(
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentRequestListResponse:
    return await hr_list_pending_request_approvals(db, current_user.user_id)


@document_extra_router.get(
    "/applications/{application_id}/document-requests",
    response_model=DocumentRequestListResponse,
    summary="List all document requests for a case",
)
async def api_list_document_requests(
    application_id: uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                  = Depends(get_current_user),
) -> DocumentRequestListResponse:
    return await list_document_requests_for_application(db, current_user.user_id, application_id)


@document_extra_router.get(
    "/documents/requests/my-pending",
    response_model=DocumentRequestListResponse,
    summary="Client — view my pending document requests",
    description="Only ever shows requests already approved by HR (status='pending') "
                 "— an attorney's request sitting in 'pending_hr_approval' never appears here.",
)
async def api_my_pending_requests(
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentRequestListResponse:
    return await list_my_pending_requests(db, current_user.user_id)


@document_extra_router.patch(
    "/documents/requests/{request_id}/cancel",
    summary="Attorney/HR cancels a pending document request",
)
async def api_cancel_document_request(
    request_id: uuid.UUID,
    db:         AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> dict:
    return await cancel_document_request(db, current_user.user_id, request_id)


# =============================================================================
# UPLOAD ON BEHALF OF A CLIENT
# =============================================================================

@document_extra_router.post(
    "/documents/upload-for-client",
    response_model=DocumentResponse,
    status_code=201,
    summary="Attorney/HR uploads a document on behalf of a client",
    description=(
        "HR-relay rule: an ATTORNEY's upload is staged as 'pending_hr_release' — "
        "invisible to the client, no notification sent — until HR approves it "
        "via PATCH /documents/{document_id}/hr-review. HR's own upload goes "
        "straight through and notifies the client immediately, as before."
    ),
)
async def api_upload_document_for_client(
    application_id: uuid.UUID    = Form(...),
    document_type:  str          = Form(...),
    category:       str          = Form(...),
    file:           UploadFile   = File(...),
    db:             AsyncSession = Depends(get_db),
    current_user                  = Depends(get_current_user),
) -> DocumentResponse:
    return await upload_document_for_client(
        db=db, actor_id=current_user.user_id, application_id=application_id,
        document_type=document_type, category=category, file=file,
    )


@document_extra_router.patch(
    "/documents/{document_id}/hr-review",
    response_model=DocumentResponse,
    summary="HR: approve or decline an attorney-uploaded document before it reaches the client",
    description="Only valid while the document is 'pending_hr_release'. "
                 "`reason` is required when declining.",
)
async def api_hr_review_uploaded_document(
    document_id: uuid.UUID,
    payload:     HRReviewUploadedDocument,
    db:          AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> DocumentResponse:
    return await hr_review_uploaded_document(
        db, current_user.user_id, document_id, payload.decision.value, payload.reason,
    )


@document_extra_router.get(
    "/documents/pending-hr-release",
    response_model=DocumentListResponse,
    summary="HR: queue of attorney-uploaded documents awaiting my release decision",
)
async def api_hr_list_pending_document_releases(
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentListResponse:
    return await hr_list_pending_document_releases(db, current_user.user_id)
