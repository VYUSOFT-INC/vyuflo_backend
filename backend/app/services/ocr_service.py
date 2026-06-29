# app/services/ocr_service.py
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from fastapi import HTTPException

from app.models.visamodels import Document, DocumentOCRField
from app.schemas.ocr import OCRFieldResponse, SaveOCRFieldsRequest
from app.services.services import db_update


async def get_ocr_fields(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> list[OCRFieldResponse]:
    """
    GET /documents/:id/ocr-fields
    Returns saved OCR fields from DB.
    Empty list = not yet extracted (frontend should call OCR service).
    """
    # Verify ownership
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.user_id != user_id:
        raise HTTPException(403, "Access denied")

    result = await db.execute(
        select(DocumentOCRField)
        .where(DocumentOCRField.document_id == document_id)
        .order_by(DocumentOCRField.created_at)
    )
    fields = result.scalars().all()
    return [OCRFieldResponse.model_validate(f) for f in fields]


async def save_ocr_fields(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
    payload:     SaveOCRFieldsRequest,
) -> list[OCRFieldResponse]:
    """
    POST /documents/:id/ocr-fields
    Called ONCE after OCR service runs.
    Saves all extracted fields to DB.
    Updates document.ocr_status = "completed".
    """
    # Verify ownership
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.user_id != user_id:
        raise HTTPException(403, "Access denied")

    # Delete any existing fields (re-run case)
    await db.execute(
        delete(DocumentOCRField)
        .where(DocumentOCRField.document_id == document_id)
    )

    # Insert new fields
    new_fields = []
    for field in payload.fields:
        ocr_field = DocumentOCRField(
            document_id      = document_id,
            field_name       = field.field_name,
            extracted_value  = field.extracted_value,
            confidence_score = field.confidence_score,
            needs_review     = field.needs_review,
            is_confirmed     = field.confidence_score >= 90 and not field.needs_review,
            created_by       = user_id,
        )
        db.add(ocr_field)
        new_fields.append(ocr_field)

    await db.flush()  # get IDs without committing

    # Update document ocr_status + average confidence
    avg_conf = (
        sum(f.confidence_score for f in payload.fields) // len(payload.fields)
        if payload.fields else 0
    )
    await db_update(db, Document, document_id, {
        "ocr_status":    "completed",
        "ocr_confidence": avg_conf,
        "modified_by":   user_id,
    })

    await db.commit()
    for f in new_fields:
        await db.refresh(f)

    return [OCRFieldResponse.model_validate(f) for f in new_fields]


async def confirm_all_fields(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> dict:
    """
    POST /documents/:id/ocr-fields/confirm-all
    Marks all fields as confirmed.
    Updates document.ocr_status = "confirmed".
    This is what "Approve All" button calls.
    """
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.user_id != user_id:
        raise HTTPException(403, "Access denied")

    now = datetime.now(timezone.utc)

    await db.execute(
        update(DocumentOCRField)
        .where(DocumentOCRField.document_id == document_id)
        .values(
            is_confirmed = True,
            needs_review = False,
            confirmed_by = user_id,
            confirmed_at = now,
        )
    )

    await db_update(db, Document, document_id, {
        "ocr_status":  "confirmed",
        "verified_by": user_id,
        "verified_at": now,
        "status":      "verified",   # document status also becomes verified
        "modified_by": user_id,
    })

    await db.commit()
    return { "detail": "All fields confirmed.", "document_id": str(document_id) }


async def update_ocr_field(
    db:       AsyncSession,
    field_id: uuid.UUID,
    user_id:  uuid.UUID,
    extracted_value: str,
    is_confirmed:    bool,
) -> OCRFieldResponse:
    """
    PATCH /documents/:id/ocr-fields/:field_id
    User edited a single field value and confirmed it.
    """
    field = await db.get(DocumentOCRField, field_id)
    if not field:
        raise HTTPException(404, "OCR field not found")

    field.extracted_value = extracted_value
    field.is_confirmed    = is_confirmed
    field.needs_review    = False
    if is_confirmed:
        field.confirmed_by = user_id
        field.confirmed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(field)
    return OCRFieldResponse.model_validate(field)



# ── services/ocr_service.py ──────────────────────────────────────────────────

async def save_or_update_ocr_fields(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
    payload:     SaveOCRFieldsRequest,
) -> list[OCRFieldResponse]:
    """
    POST /documents/:id/ocr-fields/save
    Smart upsert:
      - No existing fields → INSERT all (first open after OCR)
      - Existing fields    → UPDATE each by field_id (re-open / user edits)
    Always marks all fields confirmed and updates document status.
    """
    # Verify ownership
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.user_id != user_id:
        raise HTTPException(403, "Access denied")

    now = datetime.now(timezone.utc)

    # Check if fields already exist for this document
    result = await db.execute(
        select(DocumentOCRField)
        .where(DocumentOCRField.document_id == document_id)
    )
    existing_fields = result.scalars().all()
    existing_map = {str(f.id): f for f in existing_fields}

    final_fields: list[DocumentOCRField] = []

    if not existing_fields:
        # ── FIRST OPEN: INSERT all fields ────────────────────────────────────
        for field in payload.fields:
            ocr_field = DocumentOCRField(
                document_id      = document_id,
                field_name       = field.field_name,
                extracted_value  = field.extracted_value,
                confidence_score = field.confidence_score,
                needs_review     = False,
                is_confirmed     = True,
                confirmed_by     = user_id,
                confirmed_at     = now,
                created_by       = user_id,
            )
            db.add(ocr_field)
            final_fields.append(ocr_field)

        await db.commit()

    else:
        # ── RE-OPEN: UPDATE each field by field_id ───────────────────────────
        for field in payload.fields:
            # field.id must be sent from frontend for update path
            fid = str(getattr(field, "id", None) or "")
            if fid and fid in existing_map:
                existing = existing_map[fid]
                existing.extracted_value = field.extracted_value
                existing.is_confirmed    = True
                existing.needs_review    = False
                existing.confirmed_by    = user_id
                existing.confirmed_at    = now
                final_fields.append(existing)
            else:
                # field_id not matched — skip or log
                continue

    # ── Update document status (both paths) ──────────────────────────────────
    avg_conf = (
        sum(f.confidence_score for f in payload.fields) // len(payload.fields)
        if payload.fields else 0
    )
    await db_update(db, Document, document_id, {
        "ocr_status":    "confirmed",
        "ocr_confidence": avg_conf,
        "verified_by":   user_id,
        "verified_at":   now,
        "status":        "verified",
        "modified_by":   user_id,
    })

    await db.commit()
    for f in final_fields:
        await db.refresh(f)

    return [OCRFieldResponse.model_validate(f) for f in final_fields]