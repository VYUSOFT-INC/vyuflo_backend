"""
template_library_schema.py — Pydantic schemas for Template Library (Screen 22).

"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# TEMPLATE CARD — one card in the grid
# ===========================================================================

class LetterTemplateResponse(BaseModel):
    """
    One card in the Template Library grid.
    Powers: card badge, title, description, page/use counts, buttons.
    """
    model_config = ConfigDict(from_attributes=True)

    id:            uuid.UUID
    title:         str
    description:   Optional[str] = None

    template_type: str = Field(
        ...,
        description="cover_letter | support_letter | rfe_response | petition_statement",
    )
    # Shown as category badge on each card: "Cover Letter", "Support Letter" etc.

    visa_type_code: Optional[str] = Field(
        None,
        description="e.g. H-1B, O-1A, L-1A, TN — shown as first badge on card",
    )

    page_count: Optional[int] = Field(None, description="e.g. 4 → shown as '4 Pgs'")
    use_count:  int            = Field(0,    description="e.g. 124 → shown as '124 Uses'")

    is_platform: bool = Field(
        ...,
        description="False = My Templates, True = Platform Templates",
    )
    is_active: bool

    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# TEMPLATE LIST RESPONSE — paginated grid
# ===========================================================================

class LetterTemplateListResponse(BaseModel):
    """
    GET /templates — paginated template library.
    Drives the grid + "Showing 1 to 6 of 42 templates" footer.
    """
    items:      List[LetterTemplateResponse]
    total:      int    # 42 in "Showing 1 to 6 of 42 templates"
    page:       int
    page_size:  int
    total_pages: int


# ===========================================================================
# TEMPLATE DETAIL — Preview button
# ===========================================================================

class LetterTemplateDetailResponse(LetterTemplateResponse):
    """
    GET /templates/{id} — full template including body content.
    Used by the Preview button to show full letter content.
    """
    body_content: str   # full letter text with {{placeholders}}


# ===========================================================================
# CREATE TEMPLATE — "+ Create Template" button
# ===========================================================================

class LetterTemplateCreate(BaseModel):
    """
    POST /templates — "+ Create Template" button.
    Creates a personal (My Templates) template — is_platform always False for attorneys.
    """
    title:         str             = Field(..., min_length=1, max_length=300)
    description:   Optional[str]  = Field(None, max_length=1000)
    body_content:  str             = Field(..., min_length=1)

    template_type: str = Field(
        ...,
        description="cover_letter | support_letter | rfe_response | petition_statement",
    )
    visa_type_code: Optional[str] = Field(
        None,
        description="e.g. H-1B, O-1A, L-1A, TN — leave null if applies to all",
    )
    page_count: Optional[int] = Field(None, ge=1)


# ===========================================================================
# UPDATE TEMPLATE — 3-dot menu → Edit
# ===========================================================================

class LetterTemplateUpdate(BaseModel):
    """
    PATCH /templates/{id} — all fields optional, only provided fields written.
    Blocked for platform templates (is_platform=True) unless user is app_admin.
    """
    title:          Optional[str] = Field(None, min_length=1, max_length=300)
    description:    Optional[str] = Field(None, max_length=1000)
    body_content:   Optional[str] = Field(None, min_length=1)
    template_type:  Optional[str] = None
    visa_type_code: Optional[str] = None
    page_count:     Optional[int] = Field(None, ge=1)
    is_active:      Optional[bool] = None


# ===========================================================================
# USE TEMPLATE — "Use" button → links to application, creates Document
# ===========================================================================

class UseTemplateRequest(BaseModel):
    """
    POST /templates/{id}/use
    "Use" button — links template to an application and creates a Document record.
    """
    application_id: uuid.UUID = Field(
        ...,
        description="The application this letter is being created for",
    )
    # Optional: attorney can override the title before generating
    custom_title: Optional[str] = Field(
        None,
        max_length=300,
        description="Override document title. Defaults to template title if omitted.",
    )


class UseTemplateResponse(BaseModel):
    """
    Response after "Use" button — returns the created Document record reference.
    Frontend uses document_id to redirect to the document editor/viewer.
    """
    model_config = ConfigDict(from_attributes=True)

    document_id:    uuid.UUID    # newly created Document.id
    application_id: uuid.UUID
    template_id:    uuid.UUID
    document_title: str          # title used for the created document
    message:        str = "Document created from template. You can now edit and finalise it."
