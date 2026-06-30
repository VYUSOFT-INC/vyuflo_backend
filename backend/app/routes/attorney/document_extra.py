# =============================================================================
# app/routers/document_extra.py
#
# NEW endpoints only — 7 new APIs + filtered list.
# Your existing app/routers/document.py is NOT touched.
#
# Register in main.py alongside your existing router:
#
#   from app.routers.document_extra import document_extra_router
#   app.include_router(document_extra_router, prefix="/api/v1", tags=["Documents"])
#
# Permission codes match your existing seeds.py dot-notation exactly.
# =============================================================================

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user

# Your existing schema — reused directly
from app.schemas.document import DocumentListResponse, DocumentResponse

# New schemas — separate file, no conflict
from app.schemas.attorney.document_extra import (
    DocumentActivityListResponse,
    DocumentPageListResponse,
    DocumentStatusUpdate,
    DocumentVersionListResponse,
    RejectedDocumentListResponse, 
)

# Your existing service — reused for get_document_file_url
from app.services.document_service import get_document_file_url

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
)

document_extra_router = APIRouter()


# ── GET /documents  (with filters) ───────────────────────────────────────────
# Only use this if you want to replace your existing list endpoint with
# filter support. If your existing GET /documents is already registered,
# register this under a different path e.g. /documents/search, OR
# remove the existing one and use only this.
#
# RECOMMENDATION: keep your existing GET /documents as-is and use this
# as GET /documents/filter for now — zero conflict, zero risk.

@document_extra_router.get(
    "/documents/filter",
    response_model=DocumentListResponse,
    summary="List documents with optional filters (status, category, type)",
)
async def api_list_documents_filtered(
    application_id: Optional[uuid.UUID] = Query(None),
    status:         Optional[str]       = Query(None, description="required|uploaded|pending_review|verified|rejected|missing"),
    category:       Optional[str]       = Query(None, description="identity|employment|education|legal|personal|other"),
    document_type:  Optional[str]       = Query(None, description="Matches DocumentType.name exactly"),
    db:             AsyncSession        = Depends(get_db),
    current_user                        = Depends(get_current_user),
) -> DocumentListResponse:
    return await list_documents_filtered(
        db             = db,
        user_id        = current_user.user_id,
        application_id = application_id,
        status         = status,
        category       = category,
        document_type  = document_type,
    )
# ── GET /documents/my-rejected ───────────────────────────────────────────────
@document_extra_router.get(
    "/documents/my-rejected",
    response_model=RejectedDocumentListResponse,
    summary="Get all rejected documents for the logged-in client (Action Required)",
)
async def api_get_my_rejected_documents(
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
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
    current_user              = Depends(get_current_user),
):
    doc       = await get_document_file_url(db, document_id, current_user.user_id)
    file_path = f"./{doc['file_path']}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk.")

    fmt = doc["file_format"].lower()
    media_types = {
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "png":  "image/png",
        "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    media_type = media_types.get(fmt, "application/octet-stream")

    return FileResponse(
        path       = file_path,
        media_type = media_type,
        filename   = doc["file_name"],
        headers    = {"Content-Disposition": f'attachment; filename="{doc["file_name"]}"'},
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
    current_user              = Depends(get_current_user),
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
    current_user              = Depends(get_current_user),
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
    current_user              = Depends(get_current_user),
) -> dict:
    return await delete_document(db, document_id, current_user.user_id)


# ── PATCH /documents/{id}/status ─────────────────────────────────────────────
@document_extra_router.patch(
    "/documents/{document_id}/status",
    response_model=DocumentResponse,
    summary="Verify or reject a document — Attorney / HR / Admin only",
)
async def api_update_document_status(
    document_id:  uuid.UUID,
    payload:      DocumentStatusUpdate,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> DocumentResponse:
    return await update_document_status(
        db               = db,
        document_id      = document_id,
        reviewer_id      = current_user.user_id,
        new_status       = payload.status,
        rejection_reason = payload.rejection_reason,
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
    current_user              = Depends(get_current_user),
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
    current_user              = Depends(get_current_user),
) -> dict:
    return await trigger_ocr(db, document_id, current_user.user_id)
