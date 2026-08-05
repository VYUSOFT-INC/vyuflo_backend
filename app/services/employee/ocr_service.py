# app/services/ocr_service.py
import uuid
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from fastapi import HTTPException

from app.models.visamodels import Document, DocumentOCRField, DocumentType
from app.schemas.employee.ocr import OCRFieldResponse, SaveOCRFieldsRequest
from app.services.employee.services import db_update
from app.services.employee.document_field_config_service import get_document_field_config


# ─────────────────────────────────────────────────────────────────────────────
# EXPIRY AUTO-FILL
# ─────────────────────────────────────────────────────────────────────────────

async def _apply_expiry_from_fields(
    db: AsyncSession,
    doc_id: uuid.UUID,
    doc_type_id: uuid.UUID,
    fields: list[DocumentOCRField],
    user_id: uuid.UUID,
) -> None:
    doc_type = await db.get(DocumentType, doc_type_id)
    if not doc_type or not doc_type.ocr_slug:
        return

    config = await get_document_field_config(db, doc_type.ocr_slug)
    if not config or not config.expiry_field_name:
        return

    by_name = {f.field_name: f for f in fields}
    field = by_name.get(config.expiry_field_name)
    if not field or not field.is_confirmed:
        return

    raw = (field.extracted_value or "").strip()
    try:
        expiry = date.fromisoformat(raw)
    except ValueError:
        return

    await db_update(db, Document, doc_id, {
        "expiry_date": expiry,
        "modified_by": user_id,
    })


# ─────────────────────────────────────────────────────────────────────────────
# GET — flags each field with is_mandatory, synthesizes missing-mandatory rows
# ─────────────────────────────────────────────────────────────────────────────

async def get_ocr_fields(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> list[OCRFieldResponse]:
    """
    GET /documents/:id/ocr-fields
    Returns saved OCR fields, each flagged with is_mandatory per the admin's
    DocumentFieldConfiguration for this document's type. Mandatory fields
    OCR failed to extract at all are synthesized as empty placeholder rows
    (confidence 0, needs_review=True) so the UI can surface "this is
    required but missing" instead of silently omitting it.

    Confirmed working: OCRFieldResponse.id is Optional, so id=None for
    synthesized rows validates fine. The one field that DID need adding
    was confirmed_at (also required by the schema) — now set to None below.
    """
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
    fields = list(result.scalars().all())

    # CRITICAL: if OCR has never run on this document at all, return an
    # empty list — NOT synthesized placeholders. The frontend's loadFields()
    # checks `saved.length > 0` to decide whether to call real OCR extraction
    # or trust existing data. If we always returned something (even fake
    # placeholders), the frontend would think OCR already ran and would
    # NEVER actually call /ocr-extract, permanently showing empty fields.
    if not fields:
        return []

    doc_type = await db.get(DocumentType, doc.document_type_id)
    mandatory_fields: list[str] = []
    if doc_type and doc_type.ocr_slug:
        config = await get_document_field_config(db, doc_type.ocr_slug)
        if config:
            mandatory_fields = config.mandatory_fields

    existing_names = {f.field_name for f in fields}

    responses: list[OCRFieldResponse] = []
    for f in fields:
        resp = OCRFieldResponse.model_validate(f)
        resp.is_mandatory = f.field_name in mandatory_fields
        responses.append(resp)

    for missing_name in mandatory_fields:
        if missing_name in existing_names:
            continue
        responses.append(OCRFieldResponse(
            id=None,  # confirmed working — OCRFieldResponse.id is Optional
            document_id=document_id,
            field_name=missing_name,
            extracted_value="",
            confidence_score=0,
            needs_review=True,
            is_confirmed=False,
            is_mandatory=True,
            confirmed_at=None,  # ← ADDED — this field is required by the schema
        ))

    return responses


# ─────────────────────────────────────────────────────────────────────────────
# SAVE (first extraction) — unchanged logic, expiry auto-fill still applies
# ─────────────────────────────────────────────────────────────────────────────

async def save_ocr_fields(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
    payload:     SaveOCRFieldsRequest,
) -> list[OCRFieldResponse]:
    """
    POST /documents/:id/ocr-fields
    Called ONCE after OCR service runs.
    """
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.user_id != user_id:
        raise HTTPException(403, "Access denied")

    await db.execute(
        delete(DocumentOCRField)
        .where(DocumentOCRField.document_id == document_id)
    )

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

    await db.flush()

    avg_conf = (
        sum(f.confidence_score for f in payload.fields) // len(payload.fields)
        if payload.fields else 0
    )
    await db_update(db, Document, document_id, {
        "ocr_status":    "completed",
        "ocr_confidence": avg_conf,
        "modified_by":   user_id,
    })

    await _apply_expiry_from_fields(db, document_id, doc.document_type_id, new_fields, user_id)

    await db.commit()
    for f in new_fields:
        await db.refresh(f)

    return [OCRFieldResponse.model_validate(f) for f in new_fields]


# ─────────────────────────────────────────────────────────────────────────────
# CONFIRM ALL — separate entry point ("Approve All"), keeps its own
# mandatory-field validation as defense-in-depth even though DocumentViewer's
# Submit button doesn't call this one.
# ─────────────────────────────────────────────────────────────────────────────

async def confirm_all_fields(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> dict:
    """
    POST /documents/:id/ocr-fields/confirm-all
    """
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.user_id != user_id:
        raise HTTPException(403, "Access denied")

    doc_type = await db.get(DocumentType, doc.document_type_id)
    if doc_type and doc_type.ocr_slug:
        config = await get_document_field_config(db, doc_type.ocr_slug)
        if config and config.mandatory_fields:
            result = await db.execute(
                select(DocumentOCRField).where(DocumentOCRField.document_id == document_id)
            )
            existing = {f.field_name: f.extracted_value for f in result.scalars().all()}
            missing = [
                name for name in config.mandatory_fields
                if not (existing.get(name) or "").strip()
            ]
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot confirm — missing required field(s): {', '.join(missing)}",
                )

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
        "status":      "verified",
        "modified_by": user_id,
    })

    result = await db.execute(
        select(DocumentOCRField).where(DocumentOCRField.document_id == document_id)
    )
    confirmed_fields = result.scalars().all()
    await _apply_expiry_from_fields(db, document_id, doc.document_type_id, confirmed_fields, user_id)

    await db.commit()
    return { "detail": "All fields confirmed.", "document_id": str(document_id) }


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE SINGLE FIELD — unchanged
# ─────────────────────────────────────────────────────────────────────────────

async def update_ocr_field(
    db:       AsyncSession,
    field_id: uuid.UUID,
    user_id:  uuid.UUID,
    extracted_value: str,
    is_confirmed:    bool,
) -> OCRFieldResponse:
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

    if is_confirmed:
        doc = await db.get(Document, field.document_id)
        if doc:
            await _apply_expiry_from_fields(db, doc.id, doc.document_type_id, [field], user_id)
            await db.commit()

    return OCRFieldResponse.model_validate(field)


# ─────────────────────────────────────────────────────────────────────────────
# SAVE-OR-UPDATE (upsert) — the REAL Submit-button path. Mandatory field
# validation lives HERE now, checked against the incoming payload (what the
# user is about to save) before anything is persisted.
# ─────────────────────────────────────────────────────────────────────────────

async def save_or_update_ocr_fields(
    db:          AsyncSession,
    document_id: uuid.UUID,
    user_id:     uuid.UUID,
    payload:     SaveOCRFieldsRequest,
) -> list[OCRFieldResponse]:
    """
    POST /documents/:id/ocr-fields/save
    This is what DocumentViewer.tsx's Submit/Update button actually calls.
    """
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.user_id != user_id:
        raise HTTPException(403, "Access denied")

    # Validate mandatory fields BEFORE persisting anything, against what's
    # in the incoming payload — the frontend already blocks this client-side
    # (see useOCR.ts's submitFields), but this is the real enforcement point
    # since client-side checks can always be bypassed.
    doc_type = await db.get(DocumentType, doc.document_type_id)
    if doc_type and doc_type.ocr_slug:
        config = await get_document_field_config(db, doc_type.ocr_slug)
        if config and config.mandatory_fields:
            incoming = {f.field_name: (f.extracted_value or "").strip() for f in payload.fields}
            missing = [name for name in config.mandatory_fields if not incoming.get(name)]
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot save — missing required field(s): {', '.join(missing)}",
                )

    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(DocumentOCRField)
        .where(DocumentOCRField.document_id == document_id)
    )
    existing_fields = result.scalars().all()
    existing_map = {str(f.id): f for f in existing_fields}

    final_fields: list[DocumentOCRField] = []

    if not existing_fields:
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
        for field in payload.fields:
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
                # NEW field not previously in DB (e.g. user filled in a
                # synthesized missing-mandatory placeholder for the first
                # time) — insert it instead of silently dropping it.
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

    await _apply_expiry_from_fields(db, document_id, doc.document_type_id, final_fields, user_id)

    await db.commit()
    for f in final_fields:
        await db.refresh(f)

    return [OCRFieldResponse.model_validate(f) for f in final_fields]