# =============================================================================
# app/routers/secure_messages_router.py
# Screen 12 — Secure Messages
#
# Register in main.py:
#   from app.routers.secure_messages_router import secure_messages_router
#   app.include_router(secure_messages_router, prefix="/api/v1", tags=["Screen 12 - Secure Messages"])
#
# IMPORTANT: Register this BEFORE your existing message_router so that
#   GET /messages/templates  is not shadowed by  /messages/conversations/{id}
#
# Endpoints (new):
#   GET    /messages/templates          — chip bar (all authenticated users)
#   POST   /messages/templates          — create template (admin)
#   PATCH  /messages/templates/{id}     — update template (admin)
#   DELETE /messages/templates/{id}     — soft-delete (admin)
#
# Endpoints (enhanced existing — replaces 2 in message.py):
#   GET    /messages/conversations             — now supports ?search=
#   GET    /messages/conversations/{thread_id} — now returns case_number, visa_type_code
#
# All other existing message endpoints (send, read, mark-read, create thread)
# in message.py are REUSED AS-IS — not duplicated here.
# =============================================================================

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.attorney.secure_messages import (
    MessageTemplateCreate,
    MessageTemplateListResponse,
    MessageTemplateResponse,
    MessageTemplateUpdate,
)
from app.services.attorney.secure_messages_service import (
    service_create_message_template,
    service_delete_message_template,
    service_get_thread,
    service_list_message_templates,
    service_list_threads,
    service_update_message_template,
)

# Import your existing schemas for ThreadResponse — reused directly
from app.schemas.message import ThreadListResponse, ThreadResponse

secure_messages_router = APIRouter()


# =============================================================================
# MESSAGE TEMPLATES — chip bar on compose box
# =============================================================================

@secure_messages_router.get(
    "/messages/templates",
    response_model=MessageTemplateListResponse,
    status_code=status.HTTP_200_OK,
    summary="List reply template chips — Screen 12 compose bar",
    description=(
        "Returns all active message templates ordered by sort_order. "
        "These are the clickable chips above the compose box: "
        "'Please re-upload cleaner scan', 'Document approved', etc. "
        "Filter by category: document | approval | general | follow_up"
    ),
)
async def api_list_message_templates(
    category:     Optional[str] = Query(None, description="document | approval | general | follow_up"),
    db:           AsyncSession  = Depends(get_db),
    current_user                = Depends(get_current_user),
) -> MessageTemplateListResponse:
    data = await service_list_message_templates(db, category=category)
    return MessageTemplateListResponse(
        items=[MessageTemplateResponse.model_validate(t) for t in data["items"]],
        total=data["total"],
    )


@secure_messages_router.post(
    "/messages/templates",
    response_model=MessageTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a reply template chip (admin)",
    description=(
        "name — short chip label (keep under 40 chars for UI fit). "
        "body — full message text injected into compose box on click."
    ),
)
async def api_create_message_template(
    payload:      MessageTemplateCreate,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> MessageTemplateResponse:
    template = await service_create_message_template(
        db         = db,
        name       = payload.name,
        body       = payload.body,
        created_by = current_user.user_id,
        category   = payload.category,
        sort_order = payload.sort_order,
        is_active  = payload.is_active,
    )
    return MessageTemplateResponse.model_validate(template)


@secure_messages_router.patch(
    "/messages/templates/{template_id}",
    response_model=MessageTemplateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a reply template (admin)",
)
async def api_update_message_template(
    template_id:  uuid.UUID,
    payload:      MessageTemplateUpdate,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> MessageTemplateResponse:
    template = await service_update_message_template(
        db          = db,
        template_id = template_id,
        modified_by = current_user.user_id,
        name        = payload.name,
        body        = payload.body,
        category    = payload.category,
        sort_order  = payload.sort_order,
        is_active   = payload.is_active,
    )
    return MessageTemplateResponse.model_validate(template)


@secure_messages_router.delete(
    "/messages/templates/{template_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate a reply template (admin)",
    description="Soft-delete — sets is_active=False. Data preserved for audit.",
)
async def api_delete_message_template(
    template_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> dict:
    return await service_delete_message_template(
        db          = db,
        template_id = template_id,
        deleted_by  = current_user.user_id,
    )


# =============================================================================
# ENHANCED THREAD ENDPOINTS
# These replace the 2 corresponding endpoints in your existing message.py.
# Remove GET /messages/conversations and GET /messages/conversations/{thread_id}
# from message.py and use these instead.
# =============================================================================

@secure_messages_router.get(
    "/messages/conversations",
    response_model=ThreadListResponse,
    status_code=status.HTTP_200_OK,
    summary="List conversations — Screen 12 left panel (enhanced with search)",
    description=(
        "Returns all message threads the current user participates in, "
        "sorted by most recent message. "
        "Each thread now includes: action_required, thread_status, "
        "case_number (e.g. #VF-8915), visa_type_code (e.g. H-1B). "
        "Use ?search= to filter by case number, thread title, or last message."
    ),
)
async def api_list_threads(
    search:       Optional[str] = Query(None, description="Search by case number, title, or last message"),
    db:           AsyncSession  = Depends(get_db),
    current_user                = Depends(get_current_user),
) -> ThreadListResponse:
    return await service_list_threads(db, current_user.user_id, search=search)


@secure_messages_router.get(
    "/messages/conversations/{thread_id}",
    response_model=ThreadResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation thread — Screen 12 right panel header",
    description=(
        "Returns thread header with participant list. "
        "Now includes case_number and visa_type_code from the linked application."
    ),
)
async def api_get_thread(
    thread_id:    uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> ThreadResponse:
    return await service_get_thread(db, thread_id, current_user.user_id)
