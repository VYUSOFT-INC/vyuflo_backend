"""

Route map (6 endpoints):

  GET    /templates                → Template Library grid (list + filter + search + paginate)
  GET    /templates/{id}           → Single template detail (Preview button)
  POST   /templates                → Create Template button
  PATCH  /templates/{id}           → Edit template (3-dot menu → Edit)
  DELETE /templates/{id}           → Delete template (3-dot menu → Delete)
  POST   /templates/{id}/use       → Use button → creates Document linked to application

"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.visamodels import User
from app.services.attorney import template_library_service
from app.schemas.attorney.template_library import (
    LetterTemplateCreate,
    LetterTemplateDetailResponse,
    LetterTemplateListResponse,
    LetterTemplateUpdate,
    UseTemplateRequest,
    UseTemplateResponse,
)

template_library_router = APIRouter()


# ===========================================================================
# A. TEMPLATE LIBRARY GRID
# ===========================================================================

@template_library_router.get(
    "/templates",
    response_model=LetterTemplateListResponse,
    summary="Template Library grid — Screen 22",
)
async def list_templates(
    # My Templates / Platform Templates toggle
    is_platform: Optional[bool] = Query(
        None,
        description="false = My Templates | true = Platform Templates | omit = All",
    ),
    # Category tabs: All Templates | Cover Letters | Support Letters | RFE Responses | Petition Statements
    template_type: Optional[str] = Query(
        None,
        description="cover_letter | support_letter | rfe_response | petition_statement",
    ),
    # Visa type badge filter
    visa_type_code: Optional[str] = Query(
        None,
        description="e.g. H-1B, O-1A, L-1A, TN",
    ),
    # Search bar
    search: Optional[str] = Query(
        None,
        description="Search by title or description",
    ),
    # Pagination — "Showing 1 to 6 of 42 templates"
    page:      int = Query(default=1,  ge=1),
    page_size: int = Query(default=6,  ge=1, le=50),

    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    # _perm:        None         = Depends(require_permission("content.manage_guides")),
) -> LetterTemplateListResponse:
    """
    Screen 22 — powers the full template grid.

    Toggle behaviour:
    - My Templates (is_platform=false)   → only this attorney's created templates
    - Platform Templates (is_platform=true) → all pre-seeded platform templates
    - No filter (omit)                   → both (default on page load)

    Tab behaviour:
    - All Templates (omit template_type) → all categories
    - Cover Letters                      → template_type=cover_letter
    - Support Letters                    → template_type=support_letter
    - RFE Responses                      → template_type=rfe_response
    - Petition Statements                → template_type=petition_statement

    Sort order: platform templates first → most used → newest.
    """
    return await template_library_service.list_templates(
        db             = db,
        attorney_id    = current_user.user_id,
        is_platform    = is_platform,
        template_type  = template_type,
        visa_type_code = visa_type_code,
        search         = search,
        page           = page,
        page_size      = page_size,
    )


# ===========================================================================
# B. TEMPLATE DETAIL — Preview button
# ===========================================================================

@template_library_router.get(
    "/templates/{template_id}",
    response_model=LetterTemplateDetailResponse,
    summary="Get template detail — Screen 22 Preview button",
)
async def get_template(
    template_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    # _perm:        None         = Depends(require_permission("content.manage_guides")),
) -> LetterTemplateDetailResponse:
    """
    Screen 22 — Preview button opens full template content.
    Returns body_content (full letter text with {{placeholders}}).
    Platform templates visible to all attorneys.
    Personal templates only visible to the creator.
    """
    return await template_library_service.get_template(
        db, template_id, current_user.user_id
    )


# ===========================================================================
# C. CREATE TEMPLATE — "+ Create Template" button
# ===========================================================================

@template_library_router.post(
    "/templates",
    response_model=LetterTemplateDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new template — Screen 22 '+ Create Template' button",
)
async def create_template(
    payload:      LetterTemplateCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    # _perm:        None         = Depends(require_permission("content.manage_guides")),
) -> LetterTemplateDetailResponse:
    """
    Screen 22 — '+ Create Template' button.
    Creates a personal (My Templates) template — is_platform=False always.
    Returns full template detail including body_content.

    template_type values:
      cover_letter | support_letter | rfe_response | petition_statement
    """
    return await template_library_service.create_template(
        db, current_user.user_id, payload
    )


# ===========================================================================
# D. UPDATE TEMPLATE — 3-dot menu → Edit
# ===========================================================================

@template_library_router.patch(
    "/templates/{template_id}",
    response_model=LetterTemplateDetailResponse,
    summary="Edit a template — Screen 22 3-dot menu → Edit",
)
async def update_template(
    template_id:  uuid.UUID,
    payload:      LetterTemplateUpdate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    # _perm:        None         = Depends(require_permission("content.manage_guides")),
) -> LetterTemplateDetailResponse:
    """
    Screen 22 — 3-dot menu → Edit.
    Partial update — only provided fields are written.
    Blocked for platform templates — returns 403.
    Blocked if not the template creator — returns 403.
    """
    return await template_library_service.update_template(
        db, template_id, current_user.user_id, payload
    )


# ===========================================================================
# E. DELETE TEMPLATE — 3-dot menu → Delete
# ===========================================================================

@template_library_router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a template — Screen 22 3-dot menu → Delete",
)
async def delete_template(
    template_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    # _perm:        None         = Depends(require_permission("content.manage_guides")),
) -> dict:
    """
    Screen 22 — 3-dot menu → Delete.
    Soft-delete only — sets is_active=False.
    Blocked for platform templates — returns 403.
    Blocked if not the template creator — returns 403.
    Data preserved for audit trail.
    """
    return await template_library_service.delete_template(
        db, template_id, current_user.user_id
    )


# ===========================================================================
# F. USE TEMPLATE — "Use" button
# ===========================================================================

@template_library_router.post(
    "/templates/{template_id}/use",
    response_model=UseTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Use a template — Screen 22 'Use' button",
)
async def use_template(
    template_id:  uuid.UUID,
    payload:      UseTemplateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    # _perm:        None         = Depends(require_permission("documents.upload")),
) -> UseTemplateResponse:
    """
    Screen 22 — 'Use' button.
    Links the template to a specific application and creates a Document record.

    Steps:
    1. Validates template is accessible (own or platform)
    2. Validates application is assigned to this attorney
    3. Creates a Document record (status=pending_review, is_draft=True)
    4. Increments template.use_count (updates the '124 Uses' counter)
    5. Returns document_id → frontend redirects to document editor

    The created document starts as a draft (is_draft=True).
    Attorney finalises and uploads the actual file via PATCH /documents/{id}.
    """
    return await template_library_service.use_template(
        db, template_id, current_user.user_id, payload
    )
