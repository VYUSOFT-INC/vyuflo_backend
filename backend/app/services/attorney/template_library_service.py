"""
template_library_service.py — Service layer for Template Library (Screen 22).

Functions:
  list_templates()    → GET  /templates
  get_template()      → GET  /templates/{id}
  create_template()   → POST /templates
  update_template()   → PATCH /templates/{id}
  delete_template()   → DELETE /templates/{id}
  use_template()      → POST /templates/{id}/use
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import (
    Application,
    Document,
    DocumentType,
    LetterTemplate,
)
from app.schemas.attorney.template_library import (
    LetterTemplateCreate,
    LetterTemplateDetailResponse,
    LetterTemplateListResponse,
    LetterTemplateResponse,
    LetterTemplateUpdate,
    UseTemplateRequest,
    UseTemplateResponse,
)


# ===========================================================================
# CONSTANTS
# ===========================================================================

_VALID_TYPES = {
    "cover_letter",
    "support_letter",
    "rfe_response",
    "petition_statement",
}


# ===========================================================================
# INTERNAL HELPER
# ===========================================================================

async def _get_template_or_404(
    db:          AsyncSession,
    template_id: uuid.UUID,
) -> LetterTemplate:
    result = await db.execute(
        select(LetterTemplate).where(
            LetterTemplate.id        == template_id,
            LetterTemplate.is_active == True,  # noqa: E712
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )
    return template


# ===========================================================================
# A. LIST TEMPLATES
# ===========================================================================

async def list_templates(
    db:            AsyncSession,
    attorney_id:   uuid.UUID,
    is_platform:   Optional[bool] = None,   # None = all, False = My Templates, True = Platform
    template_type: Optional[str]  = None,   # tab filter
    visa_type_code: Optional[str] = None,   # future filter
    search:        Optional[str]  = None,   # search bar
    page:          int            = 1,
    page_size:     int            = 6,
) -> LetterTemplateListResponse:
    """
    Powers the Template Library grid on Screen 22.

    My Templates toggle     → is_platform=False  (created_by = current attorney)
    Platform Templates tab  → is_platform=True   (all platform templates)
    Category tabs           → template_type filter
    Search bar              → ilike on title + description
    Pagination              → "Showing 1 to 6 of 42 templates"
    """
    query = select(LetterTemplate).where(LetterTemplate.is_active == True)  # noqa: E712

    # ── My Templates vs Platform Templates toggle ─────────────────────────────
    if is_platform is False:
        # My Templates — only this attorney's own templates
        query = query.where(
            LetterTemplate.is_platform == False,  # noqa: E712
            LetterTemplate.created_by  == attorney_id,
        )
    elif is_platform is True:
        # Platform Templates — all pre-seeded platform templates
        query = query.where(LetterTemplate.is_platform == True)  # noqa: E712
    else:
        # All — own templates + all platform templates
        query = query.where(
            or_(
                LetterTemplate.is_platform == True,   # noqa: E712
                LetterTemplate.created_by  == attorney_id,
            )
        )

    # ── Category tab filter ───────────────────────────────────────────────────
    if template_type:
        if template_type not in _VALID_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template_type '{template_type}'. "
                       f"Valid: {', '.join(_VALID_TYPES)}",
            )
        query = query.where(LetterTemplate.template_type == template_type)

    # ── Visa type badge filter ────────────────────────────────────────────────
    if visa_type_code:
        query = query.where(LetterTemplate.visa_type_code == visa_type_code)

    # ── Search bar ────────────────────────────────────────────────────────────
    if search:
        term  = f"%{search}%"
        query = query.where(
            or_(
                LetterTemplate.title.ilike(term),
                LetterTemplate.description.ilike(term),
            )
        )

    # ── Total count ───────────────────────────────────────────────────────────
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # ── Paginate — order by platform first (platform templates at top),
    #    then by use_count desc (most used first), then created_at desc ─────────
    query = (
        query
        .order_by(
            LetterTemplate.is_platform.desc(),
            LetterTemplate.use_count.desc(),
            LetterTemplate.created_at.desc(),
        )
        .limit(page_size)
        .offset((page - 1) * page_size)
    )

    result    = await db.execute(query)
    templates = result.scalars().all()
    total_pages = max(1, -(-total // page_size))   # ceiling division

    return LetterTemplateListResponse(
        items=[LetterTemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ===========================================================================
# B. GET SINGLE TEMPLATE — Preview button
# ===========================================================================

async def get_template(
    db:          AsyncSession,
    template_id: uuid.UUID,
    attorney_id: uuid.UUID,
) -> LetterTemplateDetailResponse:
    """
    Returns full template detail including body_content.
    Used by the Preview button to render the full letter text.
    Platform templates are visible to all attorneys.
    My Templates only visible to the creator.
    """
    template = await _get_template_or_404(db, template_id)

    # Visibility check — non-platform templates only visible to creator
    if not template.is_platform and template.created_by != attorney_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template.",
        )

    return LetterTemplateDetailResponse.model_validate(template)


# ===========================================================================
# C. CREATE TEMPLATE — "+ Create Template" button
# ===========================================================================

async def create_template(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    payload:     LetterTemplateCreate,
) -> LetterTemplateDetailResponse:
    """
    Creates a new personal template (is_platform=False).
    Attorneys can only create personal templates.
    Platform templates are seeded by admins only.
    """
    if payload.template_type not in _VALID_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template_type '{payload.template_type}'.",
        )

    template = LetterTemplate(
        id=uuid.uuid4(),
        title=payload.title,
        description=payload.description,
        body_content=payload.body_content,
        template_type=payload.template_type,
        visa_type_code=payload.visa_type_code,
        page_count=payload.page_count,
        use_count=0,
        is_platform=False,   # attorneys always create personal templates
        is_active=True,
        created_by=attorney_id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return LetterTemplateDetailResponse.model_validate(template)


# ===========================================================================
# D. UPDATE TEMPLATE — 3-dot menu → Edit
# ===========================================================================

async def update_template(
    db:          AsyncSession,
    template_id: uuid.UUID,
    attorney_id: uuid.UUID,
    payload:     LetterTemplateUpdate,
) -> LetterTemplateDetailResponse:
    """
    Partial update — only provided fields are written.
    Attorneys can only edit their own personal templates.
    Platform templates are read-only for attorneys.
    """
    template = await _get_template_or_404(db, template_id)

    if template.is_platform:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform templates cannot be edited. "
                   "Use '+ Create Template' to create your own version.",
        )

    if template.created_by != attorney_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own templates.",
        )

    if payload.template_type and payload.template_type not in _VALID_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template_type '{payload.template_type}'.",
        )

    now = datetime.now(timezone.utc)
    if payload.title          is not None: template.title          = payload.title
    if payload.description    is not None: template.description    = payload.description
    if payload.body_content   is not None: template.body_content   = payload.body_content
    if payload.template_type  is not None: template.template_type  = payload.template_type
    if payload.visa_type_code is not None: template.visa_type_code = payload.visa_type_code
    if payload.page_count     is not None: template.page_count     = payload.page_count
    if payload.is_active      is not None: template.is_active      = payload.is_active

    template.modified_by = attorney_id
    template.updated_at  = now

    await db.commit()
    await db.refresh(template)

    return LetterTemplateDetailResponse.model_validate(template)


# ===========================================================================
# E. DELETE TEMPLATE — 3-dot menu → Delete
# ===========================================================================

async def delete_template(
    db:          AsyncSession,
    template_id: uuid.UUID,
    attorney_id: uuid.UUID,
) -> dict:
    """
    Soft-delete — sets is_active=False.
    Attorneys can only delete their own personal templates.
    Platform templates cannot be deleted by attorneys.
    """
    template = await _get_template_or_404(db, template_id)

    if template.is_platform:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform templates cannot be deleted.",
        )

    if template.created_by != attorney_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own templates.",
        )

    template.is_active   = False
    template.modified_by = attorney_id
    template.updated_at  = datetime.now(timezone.utc)

    await db.commit()
    return {"message": "Template deleted.", "id": str(template_id)}


# ===========================================================================
# F. USE TEMPLATE — "Use" button → creates Document linked to application
# ===========================================================================

async def use_template(
    db:          AsyncSession,
    template_id: uuid.UUID,
    attorney_id: uuid.UUID,
    payload:     UseTemplateRequest,
) -> UseTemplateResponse:
    """
    "Use" button — links template to an application and creates a Document record.

    Steps:
      1. Validate template exists and is accessible
      2. Validate application exists and is assigned to this attorney
      3. Find or create a DocumentType for "Immigration Letter" (legal category)
      4. Create Document record with content derived from template
      5. Increment template.use_count
      6. Return document_id for frontend redirect to document editor
    """
    template = await _get_template_or_404(db, template_id)

    # Visibility check
    if not template.is_platform and template.created_by != attorney_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template.",
        )

    # Validate application belongs to this attorney
    app_result = await db.execute(
        select(Application).where(
            Application.id                == payload.application_id,
            Application.assigned_attorney_id == attorney_id,
        )
    )
    application = app_result.scalar_one_or_none()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or not assigned to you.",
        )

    # Find DocumentType for immigration letters (legal category)
    # Use existing "National Interest Waiver Justification Letter" or generic legal type
    doc_type_result = await db.execute(
        select(DocumentType).where(
            DocumentType.category  == "legal",
            DocumentType.is_active == True,  # noqa: E712
        )
        .limit(1)
    )
    doc_type = doc_type_result.scalar_one_or_none()

    if not doc_type:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No legal document type found. Please contact admin.",
        )

    # Determine document title
    document_title = payload.custom_title or template.title

    # Create Document record
    # Note: file_path is a placeholder — attorney will upload actual file
    # after editing the template content. file_size_kb=0 until file is attached.
    now         = datetime.now(timezone.utc)
    document_id = uuid.uuid4()

    new_document = Document(
        id=document_id,
        user_id=application.user_id,         # the applicant
        application_id=payload.application_id,
        document_type_id=doc_type.id,
        file_name=f"{document_title}.docx",
        file_path=f"templates/generated/{document_id}.docx",
        file_size_kb=0,
        file_format="docx",
        status="pending_review",
        is_draft=True,                        # starts as draft until attorney finalises
        created_by=attorney_id,
    )
    db.add(new_document)

    # Increment use_count on template
    template.use_count  += 1
    template.modified_by = attorney_id
    template.updated_at  = now

    await db.commit()

    return UseTemplateResponse(
        document_id    = document_id,
        application_id = payload.application_id,
        template_id    = template_id,
        document_title = document_title,
    )
