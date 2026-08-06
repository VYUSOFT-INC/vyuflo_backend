# # ocr_service/router.py  —  LOCAL version (no Claude, no external API)
# #
# # Same endpoint, same OCRResponse shape as before. The pipeline is now:
# #
# #     upload ──► run_ocr (PaddleOCR + passporteye)  ──► text (+ passport MRZ)
# #            └─► deterministic extract_fields(text)  ──► fixed-format fields
# #            └─► [optional] local VLM on the image   ──► fuzzy-doc fields
# #
# # Deterministic runs first and is trusted for the fixed-format docs (passport,
# # I-797, I-94, EAD, LCA, PAN, Aadhaar) because its values are checksum- or
# # format-validated. The VLM is only consulted for documents the deterministic
# # layer can't anchor (offer letters, payslips, W2, degrees, green cards) and
# # only when VLM_ENABLED=true. If the VLM is off or unreachable, the endpoint
# # still returns the deterministic result.

# from typing import Optional
# import uuid 

# from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
# from starlette.concurrency import run_in_threadpool
# from pydantic import BaseModel

# from app.core.dependencies import get_current_user
# from app.ocr.local_ocr import run_ocr, to_image_bytes
# from .vlm_fallback import extract_with_vlm, VLM_ENABLED
# from app.ocr.deterministic_extractor import extract_fields


# ocr_router = APIRouter()


# # ── response models (unchanged, so nothing downstream has to change) ──────────
# class OCRField(BaseModel):
#     field_name:       str
#     extracted_value:  str
#     confidence_score: int
#     needs_review:     bool
#     is_mandatory:     bool = False 

# class OCRResponse(BaseModel):
#     filename:      str
#     document_type: str
#     fields:        list[OCRField]
#     type_mismatch: bool = False           # ← NEW
#     expected_type: Optional[str] = None   # ← NEW


# _INDETERMINATE = {"unknown", "other"}   # OCR couldn't pin a fixed format — never a false mismatch

# # ── config ────────────────────────────────────────────────────────────────────

# # Map the deterministic layer's type names onto the vocabulary the rest of the
# # app already uses (the VLM already returns this vocabulary via its prompt).
# _TYPE_MAP = {"pan": "pan_card", "ead": "ead_card"}

# # Documents with no fixed layout — the deterministic layer won't anchor these,
# # so they're the ones worth sending to the VLM.
# _FUZZY_TYPES = {
#     "unknown", "other", "green_card",
#     "offer_letter", "salary_slip", "w2", "form_16", "degree",
# }


# def _needs_vlm(doc_type: str, fields: list[dict], ocr_confidence: int) -> bool:
#     """Consult the VLM only when the deterministic layer clearly fell short."""
#     if doc_type in _FUZZY_TYPES:
#         return True
#     if not fields:                       # recognised the type but got nothing
#         return True
#     # recognised type but every field is low-confidence AND the scan is poor
#     if ocr_confidence < 60 and not any(f["confidence_score"] >= 90 for f in fields):
#         return True
#     return False


# def _to_ocr_fields(fields: list[dict]) -> list[OCRField]:
#     """Keep only the four known keys, so stray keys can't break validation."""
#     out = []
#     for f in fields:
#         out.append(OCRField(
#             field_name=str(f["field_name"]),
#             extracted_value=str(f["extracted_value"]),
#             confidence_score=int(f["confidence_score"]),
#             needs_review=bool(f["needs_review"]),
#         ))
#     return out


# # ── endpoint ────────────────────────────────────────────────────────────────

# # ── core logic — importable directly, no HTTP round-trip needed ─────────────
# async def run_extraction(
#     content: bytes,
#     ext: str,
#     expected_doc_type: Optional[str] = None,
# ) -> OCRResponse:
#     if ext not in ("jpg", "jpeg", "png", "pdf"):
#         raise HTTPException(400, "Use JPG, PNG or PDF.")
#     if len(content) > 20 * 1024 * 1024:
#         raise HTTPException(400, "Max 20MB.")

#     # 1) OCR (CPU-bound → off the event loop)
#     try:
#         ocr = await run_in_threadpool(run_ocr, content, ext)
#     except Exception as e:
#         raise HTTPException(500, f"OCR failed: {type(e).__name__}: {e}")

#     # 2) Structured extraction
#     if ocr.passport_fields:
#         doc_type = "passport"
#         fields = ocr.passport_fields
#     else:
#         result = extract_fields(ocr.text, doc_type_hint=expected_doc_type)
#         doc_type = result.document_type
#         fields = result.fields

#     # 3) Optional local-VLM fallback for fuzzy / low-yield documents
#     if VLM_ENABLED and _needs_vlm(doc_type, fields, ocr.avg_confidence):
#         try:
#             img_bytes, media = to_image_bytes(content, ext)
#             vlm = await extract_with_vlm(img_bytes, media)
#         except Exception:
#             vlm = None
#         if vlm:
#             vlm_type, vlm_fields = vlm
#             if vlm_fields and len(vlm_fields) >= len(fields):
#                 doc_type, fields = vlm_type, vlm_fields

#     # 4) Normalise + mismatch check
#     doc_type = _TYPE_MAP.get(doc_type, doc_type)
#     type_mismatch = bool(
#         expected_doc_type
#         and doc_type not in _INDETERMINATE
#         and expected_doc_type not in _INDETERMINATE
#         and doc_type != expected_doc_type
#     )
#     return OCRResponse(
#         filename="",   # caller fills this in if needed
#         document_type=doc_type,
#         fields=_to_ocr_fields(fields),
#         type_mismatch=type_mismatch,
#         expected_type=expected_doc_type,
#     )


# # ── HTTP wrapper — thin, just reads the upload and delegates ────────────────
# @ocr_router.post("/ocr/extract", response_model=OCRResponse)
# async def extract_ocr(
#     file: UploadFile = File(...),
#     expected_doc_type: Optional[str] = Form(None),
#     current_user_id: uuid.UUID = Depends(get_current_user),
# ) -> OCRResponse:
#     filename = file.filename or "upload"
#     ext = filename.rsplit(".", 1)[-1].lower()
#     content = await file.read()
#     result = await run_extraction(content, ext, expected_doc_type)
#     result.filename = filename
#     return result


# ocr_service/router.py  —  LOCAL version (no Claude, no external API)
#
# Same endpoint, same OCRResponse shape as before. The pipeline is now:
#
#     upload ──► run_ocr (PaddleOCR + passporteye)  ──► text (+ passport MRZ)
#            └─► deterministic extract_fields(text)  ──► fixed-format fields
#            └─► [optional] local VLM on the image   ──► fuzzy-doc fields
#
# Deterministic runs first and is trusted for the fixed-format docs (passport,
# I-797, I-94, EAD, LCA, PAN, Aadhaar) because its values are checksum- or
# format-validated. The VLM is only consulted for documents the deterministic
# layer can't anchor (offer letters, payslips, W2, degrees, green cards) and
# only when VLM_ENABLED=true. If the VLM is off or unreachable, the endpoint
# still returns the deterministic result.

from typing import Optional
import uuid 

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.ocr.local_ocr import run_ocr, to_image_bytes
from .vlm_fallback import extract_with_vlm, VLM_ENABLED
from app.ocr.deterministic_extractor import extract_fields


ocr_router = APIRouter()


# ── response models (unchanged, so nothing downstream has to change) ──────────
class OCRField(BaseModel):
    field_name:       str
    extracted_value:  str
    confidence_score: int
    needs_review:     bool
    is_mandatory:     bool = False 

class OCRResponse(BaseModel):
    filename:      str
    document_type: str
    fields:        list[OCRField]
    type_mismatch: bool = False           # ← NEW
    expected_type: Optional[str] = None   # ← NEW
    quality_issue: Optional[str] = None     # ← ADDED — "blurry" or None, set by the caller in document.py
    sharpness_score: Optional[float] = None # ← ADDED — for debugging/tuning the blur threshold


_INDETERMINATE = {"unknown", "other"}   # OCR couldn't pin a fixed format — never a false mismatch

# ── config ────────────────────────────────────────────────────────────────────

# Map the deterministic layer's type names onto the vocabulary the rest of the
# app already uses (the VLM already returns this vocabulary via its prompt).
_TYPE_MAP = {"pan": "pan_card", "ead": "ead_card"}

# Documents with no fixed layout — the deterministic layer won't anchor these,
# so they're the ones worth sending to the VLM.
_FUZZY_TYPES = {
    "unknown", "other", "green_card",
    "offer_letter", "salary_slip", "w2", "form_16", "degree",
}


def _needs_vlm(doc_type: str, fields: list[dict], ocr_confidence: int) -> bool:
    """Consult the VLM only when the deterministic layer clearly fell short."""
    if doc_type in _FUZZY_TYPES:
        return True
    if not fields:                       # recognised the type but got nothing
        return True
    # recognised type but every field is low-confidence AND the scan is poor
    if ocr_confidence < 60 and not any(f["confidence_score"] >= 90 for f in fields):
        return True
    return False


def _to_ocr_fields(fields: list[dict]) -> list[OCRField]:
    """Keep only the four known keys, so stray keys can't break validation."""
    out = []
    for f in fields:
        out.append(OCRField(
            field_name=str(f["field_name"]),
            extracted_value=str(f["extracted_value"]),
            confidence_score=int(f["confidence_score"]),
            needs_review=bool(f["needs_review"]),
        ))
    return out


# ── endpoint ────────────────────────────────────────────────────────────────

# ── core logic — importable directly, no HTTP round-trip needed ─────────────
async def run_extraction(
    content: bytes,
    ext: str,
    expected_doc_type: Optional[str] = None,
) -> OCRResponse:
    if ext not in ("jpg", "jpeg", "png", "pdf"):
        raise HTTPException(400, "Use JPG, PNG or PDF.")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "Max 20MB.")

    # 1) OCR (CPU-bound → off the event loop)
    try:
        ocr = await run_in_threadpool(run_ocr, content, ext)
    except Exception as e:
        raise HTTPException(500, f"OCR failed: {type(e).__name__}: {e}")

    # 2) Structured extraction
    if ocr.passport_fields:
        doc_type = "passport"
        fields = ocr.passport_fields
    else:
        result = extract_fields(ocr.text, doc_type_hint=expected_doc_type)
        doc_type = result.document_type
        fields = result.fields

    # 3) Optional local-VLM fallback for fuzzy / low-yield documents
    if VLM_ENABLED and _needs_vlm(doc_type, fields, ocr.avg_confidence):
        try:
            img_bytes, media = to_image_bytes(content, ext)
            vlm = await extract_with_vlm(img_bytes, media)
        except Exception:
            vlm = None
        if vlm:
            vlm_type, vlm_fields = vlm
            if vlm_fields and len(vlm_fields) >= len(fields):
                doc_type, fields = vlm_type, vlm_fields

    # 4) Normalise + mismatch check
    doc_type = _TYPE_MAP.get(doc_type, doc_type)
    type_mismatch = bool(
        expected_doc_type
        and doc_type not in _INDETERMINATE
        and expected_doc_type not in _INDETERMINATE
        and doc_type != expected_doc_type
    )
    return OCRResponse(
        filename="",   # caller fills this in if needed
        document_type=doc_type,
        fields=_to_ocr_fields(fields),
        type_mismatch=type_mismatch,
        expected_type=expected_doc_type,
    )


# ── HTTP wrapper — thin, just reads the upload and delegates ────────────────
@ocr_router.post("/ocr/extract", response_model=OCRResponse)
async def extract_ocr(
    file: UploadFile = File(...),
    expected_doc_type: Optional[str] = Form(None),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> OCRResponse:
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower()
    content = await file.read()
    result = await run_extraction(content, ext, expected_doc_type)
    result.filename = filename
    return result