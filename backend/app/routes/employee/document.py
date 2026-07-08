import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.employee.document import DocumentListResponse, DocumentResponse
from app.schemas.employee.ocr import OCRFieldResponse, OCRFieldUpdate, SaveOCRFieldsRequest
from app.services.employee.document_service import get_document_by_id, get_document_file_url, list_documents, upload_document
from app.services.employee.ocr_service import confirm_all_fields, get_ocr_fields, save_ocr_fields, save_or_update_ocr_fields, update_ocr_field

document_router = APIRouter()

@document_router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List documents for current user",
)
async def api_list_documents(
    application_id: Optional[uuid.UUID] = Query(None),
    db:             AsyncSession         = Depends(get_db),
    current_user:   uuid.UUID            = Depends(get_current_user),
) -> DocumentListResponse:
    return await list_documents(db, current_user.user_id, application_id)


@document_router.get(
    "/documents/{document_id}/ocr-fields",
    response_model=list[OCRFieldResponse],
    summary="Get saved OCR fields for a document",
)
async def api_get_ocr_fields(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: uuid.UUID    = Depends(get_current_user),
) -> list[OCRFieldResponse]:
    return await get_ocr_fields(db, document_id, current_user.user_id)

@document_router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Upload a document file",
)
async def api_upload_document(
    file:           UploadFile          = File(...),
    application_id: Optional[str]       = Form(None),
    document_type:  str                 = Form(...),
    category:       str                 = Form(...),
    document_request_id: Optional[str] = Form(None),   # ADD 
    db:             AsyncSession         = Depends(get_db),
    current_user:   uuid.UUID            = Depends(get_current_user),
) -> DocumentResponse:
    app_id = uuid.UUID(application_id) if application_id else None
    request_id = uuid.UUID(document_request_id) if document_request_id else None   # ← ADD

    return await upload_document(
        db, current_user.user_id, app_id, document_type, category, file,
        document_request_id=request_id,   # ADD

    )

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
    current_user: uuid.UUID    = Depends(get_current_user),
) -> list[OCRFieldResponse]:
    return await save_ocr_fields(db, document_id, current_user.user_id, payload)


@document_router.post(
    "/documents/{document_id}/ocr-fields/confirm-all",
    summary="Confirm all OCR fields (Approve All button)",
)
async def api_confirm_all_fields(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: uuid.UUID    = Depends(get_current_user),
) -> dict:
    return await confirm_all_fields(db, document_id, current_user.user_id)


# ── PATCH /documents/:id/ocr-fields/:field_id ────────────────────────────────
# User edited a single field and clicked Confirm.
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
    current_user: uuid.UUID    = Depends(get_current_user),
) -> OCRFieldResponse:
    return await update_ocr_field(
        db,
        field_id,
        current_user.user_id,
        payload.extracted_value or "",
        payload.is_confirmed or False,
    )


# router.py — add this endpoint
@document_router.get(
    "/documents/{document_id}/view",
    summary="Get document file for viewing",
)
async def api_view_document(
    document_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: uuid.UUID    = Depends(get_current_user),
):
    from fastapi.responses import FileResponse

    doc = await get_document_file_url(db, document_id, current_user.user_id)
    file_path = f"./{doc['file_path']}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk.")

    # Detect mime type
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
        headers    = {"Content-Disposition": "inline"},  # ← inline = show in browser, not download
    )

@document_router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document by ID",
)
async def api_get_document_by_id(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> DocumentResponse:
    return await get_document_by_id(
        db=db,
        current_user_id=current_user.user_id,
        document_id=document_id,
    )

# ── routers/documents.py ─────────────────────────────────────────────────────

@document_router.post(
    "/documents/{document_id}/ocr-fields/save",
    response_model=list[OCRFieldResponse],
    status_code=200,
    summary="Save or update OCR fields — upsert based on existing data",
)
async def api_save_or_update_ocr_fields(
    document_id:  uuid.UUID,
    payload:      SaveOCRFieldsRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: uuid.UUID    = Depends(get_current_user),
) -> list[OCRFieldResponse]:
    return await save_or_update_ocr_fields(
        db, document_id, current_user.user_id, payload
    )







