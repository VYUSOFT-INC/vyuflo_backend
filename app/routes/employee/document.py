
# app/routers/documents.py

import os
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from fastapi.responses import FileResponse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.core_permissions import PermissionChecker
from app.core.database import get_db
from app.core.dependencies import CurrentUserData, get_current_user
from app.models.visamodels import User
from app.ocr.ocr_service_router import OCRField, OCRResponse, run_extraction
from app.schemas.employee.document import DocumentListResponse, DocumentResponse, RenameDocumentRequest
from app.schemas.employee.ocr import OCRFieldResponse, OCRFieldUpdate, SaveOCRFieldsRequest
from app.services.employee.document_field_config_service import get_document_field_config
from app.services.employee.document_service import (
    confirm_document_ocr,
    delete_document,
    get_document_by_id,
    get_document_file_url,
    get_document_version_history,
    get_expected_ocr_slug,
    list_documents,
    list_hub_documents,
    rename_document,
    reupload_expired_document,
    reuse_document_for_case,
    upload_document,
)
from app.services.employee.ocr_service import (
    confirm_all_fields,
    get_ocr_fields,
    save_ocr_fields,
    save_or_update_ocr_fields,
    update_ocr_field,
)

document_router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────

@document_router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List documents for current user",
)
async def api_list_documents(
    application_id: Optional[uuid.UUID] = Query(None),
    db:             AsyncSession         = Depends(get_db),
    current_user                         = Depends(get_current_user),
) -> DocumentListResponse: 
    return await list_documents(db, current_user.user_id, application_id)


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

@document_router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Upload a document file",
)
async def api_upload_document(
    file:           UploadFile    = File(...),
    application_id: Optional[str] = Form(None),
    document_type:  str           = Form(...),
    category:       str           = Form(...),
    custom_name:    Optional[str] = Form(None), 
    db:             AsyncSession   = Depends(get_db),
    current_user                   = Depends(get_current_user),
) -> DocumentResponse:
    app_id = uuid.UUID(application_id) if application_id else None
    return await upload_document(
        db, current_user.user_id, app_id, document_type, category, file, custom_name
    )

@document_router.patch(
    "/documents/{document_id}/rename",
    response_model=DocumentResponse,
    summary="Rename a document's display name",
)
async def api_rename_document(
    document_id: uuid.UUID,
    payload:     RenameDocumentRequest,
    db:          AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentResponse:
    return await rename_document(db, document_id, current_user.user_id, payload.new_name)

# ─────────────────────────────────────────────────────────────────────────────
# HUB — MUST stay above every /documents/{document_id} route below.
# FastAPI matches path patterns in registration order — if this sits after
# {document_id}, a request for "hub" gets matched against {document_id}: uuid.UUID
# first and fails validation with a 422 before this handler ever runs.
# ─────────────────────────────────────────────────────────────────────────────

@document_router.get(
    "/documents/hub",
    response_model=DocumentListResponse,
    summary="List all of the current user's documents across cases — for the reuse picker",
)
async def api_list_hub_documents(
    search:       Optional[str] = Query(None),
    db:           AsyncSession  = Depends(get_db),
    current_user                = Depends(get_current_user),
) -> DocumentListResponse:
    return await list_hub_documents(db, current_user.user_id, search)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIRM OCR
# Called by frontend after user reviews and submits OCR fields.
# This is what actually marks the task as completed.
# ─────────────────────────────────────────────────────────────────────────────

@document_router.post(
    "/documents/{document_id}/confirm",
    response_model=DocumentResponse,
    summary="Confirm OCR review — completes the linked task",
)
async def api_confirm_document_ocr(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentResponse:
    return await confirm_document_ocr(db, document_id, current_user.user_id)


# ─────────────────────────────────────────────────────────────────────────────
# REUSE — attach an existing Hub document to a new case, without re-uploading
# ─────────────────────────────────────────────────────────────────────────────

@document_router.post(
    "/documents/{document_id}/reuse",
    response_model=DocumentResponse,
    status_code=201,
    summary="Reuse an existing Hub document for a new case (duplicates the file)",
)
async def api_reuse_document(
    document_id:    uuid.UUID,
    application_id: str = Form(...),
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> DocumentResponse:
    return await reuse_document_for_case(
        db, current_user.user_id, document_id, uuid.UUID(application_id)
    )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# Deletes document + OCR fields + resets task to pending.
# Used when OCR fails and user wants to re-upload a different file.
# ─────────────────────────────────────────────────────────────────────────────

@document_router.delete(
    "/documents/{document_id}",
    status_code=204,
    summary="Delete document and reset linked task to pending",
)
async def api_delete_document(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> None:
    await delete_document(db, document_id, current_user.user_id)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW (serve file inline)
# ─────────────────────────────────────────────────────────────────────────────

from fastapi.responses import StreamingResponse
from app.services.employee import storage

# @document_router.get(
#     "/documents/{document_id}/view",
#     summary="Get document file for inline viewing",
# )
# async def api_view_document(
#     document_id:  uuid.UUID,
#     db:           AsyncSession = Depends(get_db),
#     current_user               = Depends(get_current_user),
# ):
#     doc = await get_document_file_url(db, document_id, current_user.user_id)

#     fmt = doc["file_format"].lower()
#     media_types = {
#         "jpg":  "image/jpeg",
#         "jpeg": "image/jpeg",
#         "png":  "image/png",
#         "pdf":  "application/pdf",
#         "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#     }
#     media_type = media_types.get(fmt, "application/octet-stream")

#     content, _ = await storage.get_file_bytes(doc["file_path"])

#     return StreamingResponse(
#         iter([content]),
#         media_type=media_type,
#         headers={"Content-Disposition": f'inline; filename="{doc["file_name"]}"'},
#     )

@document_router.get(
    "/documents/{document_id}/view",
    summary="Get document file for inline viewing",
)
async def api_view_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[
        CurrentUserData,
        Depends(PermissionChecker(
            [
                "documents.view_own",
                "documents.view_team",
                "documents.view_assigned",
                "documents.view_all",
            ],
            require_all=False,   # holding ANY one of these passes the gate
        )),
    ] = None,
):
    # ── Layer 1 (PermissionChecker above): user holds SOME document-view capability ──
    # ── Layer 2 (inside get_document_file_url): is THIS document in scope for them? ──
    doc = await get_document_file_url(db, document_id, current_user.user_id)

    fmt = doc["file_format"].lower()
    media_types = {
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "png":  "image/png",
        "gif":  "image/gif",
        "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    media_type = media_types.get(fmt, "application/octet-stream")

    content, _ = await storage.get_file_bytes(doc["file_path"])

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{doc["file_name"]}"'},
    )

@document_router.post("/documents/{doc_id}/ocr-extract")
async def ocr_extract_for_document(
    doc_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expected_slug = await get_expected_ocr_slug(db, doc_id)
    print(f"🔍 DEBUG expected_slug = {expected_slug!r}")
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower()
    content = await file.read()

    result = await run_extraction(content, ext, expected_slug)
    result.filename = filename
    if expected_slug:
        config = await get_document_field_config(db, expected_slug)
        print(f"🔍 DEBUG expected_slug = {expected_slug!r}")
        if config and config.mandatory_fields:
            existing_names = {f.field_name for f in result.fields}
            for f in result.fields:
                f.is_mandatory = f.field_name in config.mandatory_fields
            for missing_name in config.mandatory_fields:
                if missing_name in existing_names:
                    continue
                result.fields.append(OCRField(
                    field_name=missing_name,
                    extracted_value="",
                    confidence_score=0,
                    needs_review=True,
                    is_mandatory=True,
                ))
    return result

# ─────────────────────────────────────────────────────────────────────────────
# GET BY ID
# NOTE: Must come AFTER all /documents/{id}/xxx routes to avoid route conflicts.
# ─────────────────────────────────────────────────────────────────────────────

@document_router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document by ID",
)
async def api_get_document_by_id(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentResponse:
    return await get_document_by_id(db, current_user.user_id, document_id)


# ─────────────────────────────────────────────────────────────────────────────
# OCR FIELDS
# ─────────────────────────────────────────────────────────────────────────────

@document_router.get(
    "/documents/{document_id}/ocr-fields",
    response_model=list[OCRFieldResponse],
    summary="Get saved OCR fields for a document",
)
async def api_get_ocr_fields(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> list[OCRFieldResponse]:
    return await get_ocr_fields(db, document_id, current_user.user_id)


@document_router.post(
    "/documents/{document_id}/ocr-fields",
    response_model=list[OCRFieldResponse],
    status_code=201,
    summary="Save OCR extracted fields to database",
)
async def api_save_ocr_fields(
    document_id:  uuid.UUID,
    payload:      SaveOCRFieldsRequest,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> list[OCRFieldResponse]:
    return await save_ocr_fields(db, document_id, current_user.user_id, payload)


@document_router.post(
    "/documents/{document_id}/ocr-fields/save",
    response_model=list[OCRFieldResponse],
    status_code=200,
    summary="Save or update OCR fields — upsert",
)
async def api_save_or_update_ocr_fields(
    document_id:  uuid.UUID,
    payload:      SaveOCRFieldsRequest,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> list[OCRFieldResponse]:
    return await save_or_update_ocr_fields(db, document_id, current_user.user_id, payload)


@document_router.post(
    "/documents/{document_id}/ocr-fields/confirm-all",
    summary="Confirm all OCR fields",
)
async def api_confirm_all_fields(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> dict:
    return await confirm_all_fields(db, document_id, current_user.user_id)


@document_router.patch(
    "/documents/{document_id}/ocr-fields/{field_id}",
    response_model=OCRFieldResponse,
    summary="Edit and confirm a single OCR field",
)
async def api_update_ocr_field(
    document_id:  uuid.UUID,
    field_id:     uuid.UUID,
    payload:      OCRFieldUpdate,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> OCRFieldResponse:
    return await update_ocr_field(
        db,
        field_id,
        current_user.user_id,
        payload.extracted_value or "",
        payload.is_confirmed or False,
    )



from pydantic import BaseModel
 
class ExpectedFieldItem(BaseModel):
    field_name:   str
    is_mandatory: bool
 
class ExpectedFieldsResponse(BaseModel):
    ocr_slug: str | None
    fields:   list[ExpectedFieldItem]
 
 
@document_router.get(
    "/documents/{doc_id}/expected-fields",
    response_model=ExpectedFieldsResponse,
)
async def get_expected_fields(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fast, OCR-free lookup: what fields SHOULD this document type have,
    per admin config? Returns an empty fields list for fuzzy/VLM types
    (Offer Letter, Organizational Chart, etc.) that have no fixed config —
    the frontend should fall back to a plain loading spinner in that case.
    """
    expected_slug = await get_expected_ocr_slug(db, doc_id)
    if not expected_slug:
        return ExpectedFieldsResponse(ocr_slug=None, fields=[])
 
    config = await get_document_field_config(db, expected_slug)
    if not config:
        return ExpectedFieldsResponse(ocr_slug=expected_slug, fields=[])
 
    return ExpectedFieldsResponse(
        ocr_slug=expected_slug,
        fields=[
            ExpectedFieldItem(field_name=name, is_mandatory=True)
            for name in config.mandatory_fields
        ],
    )



@document_router.post(
    "/documents/{document_id}/reupload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Re-upload a new version replacing an expired document",
)
async def api_reupload_document(
    document_id: uuid.UUID,
    file:        UploadFile = File(...),
    db:          AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> DocumentResponse:
    return await reupload_expired_document(db, document_id, current_user.user_id, file)


@document_router.get(
    "/documents/{document_id}/versions",
    summary="Get the full replacement history for a document",
)
async def api_get_document_versions(
    document_id: uuid.UUID,
    db:          AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    return await get_document_version_history(db, document_id, current_user.user_id)