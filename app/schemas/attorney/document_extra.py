# =============================================================================
# app/schemas/document_extra.py
#
# NEW schemas only — for the 7 new APIs.
# Your existing app/schemas/document.py is NOT touched.
# Import these wherever needed alongside your existing DocumentResponse.
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class DocumentStatus(str, Enum):
    required       = "required"
    uploaded       = "uploaded"
    pending_review = "pending_review"
    verified       = "verified"
    rejected       = "rejected"
    missing        = "missing"


# ── Used by: GET /documents/{id}/versions ────────────────────────────────────
class DocumentVersionResponse(BaseModel):
    id:              uuid.UUID
    version:         int
    name:            str            # file_name
    file_size_bytes: int            # file_size_kb * 1024
    file_type:       str            # file_format
    status:          DocumentStatus
    uploaded_at:     datetime       # created_at

    model_config = ConfigDict(from_attributes=True)


class DocumentVersionListResponse(BaseModel):
    items: list[DocumentVersionResponse]
    total: int


# ── Used by: GET /documents/{id}/activity ────────────────────────────────────
class DocumentActivityResponse(BaseModel):
    id:         uuid.UUID
    action:     str
    actor_id:   Optional[uuid.UUID]
    actor_type: str
    note:       Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentActivityListResponse(BaseModel):
    items: list[DocumentActivityResponse]
    total: int


# ── Used by: GET /documents/{id}/pages ───────────────────────────────────────
class DocumentPageResponse(BaseModel):
    id:             uuid.UUID
    document_id:    uuid.UUID
    page_number:    int
    thumbnail_url:  Optional[str]
    image_url:      Optional[str]
    ocr_confidence: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class DocumentPageListResponse(BaseModel):
    items: list[DocumentPageResponse]
    total: int


# ── Used by: PATCH /documents/{id}/status ────────────────────────────────────
class DocumentStatusUpdate(BaseModel):
    status:           DocumentStatus
    rejection_reason: Optional[str] = Field(
        None,
        description="Required when status = 'rejected'",
        max_length=500,
    )
# ── Used by: GET /documents/my-rejected ──────────────────────────────────────
class RejectedDocumentResponse(BaseModel):
    id:               uuid.UUID
    file_name:        str
    rejection_reason: Optional[str]
    status:           DocumentStatus
    updated_at:       datetime

    model_config = ConfigDict(from_attributes=True)


class RejectedDocumentListResponse(BaseModel):
    items: list[RejectedDocumentResponse]
    total: int
