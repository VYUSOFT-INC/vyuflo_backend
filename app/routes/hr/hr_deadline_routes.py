# app/routes/hr_deadline_routes.py
# Updated: extension endpoint now takes deadline_id (not application_id)
# because extensions are attached to a specific Deadline row.

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.hr.hr_deadline_schemas import (
    DeadlineListResponse,
    ExtensionRequestResponse,
    RequestExtensionBody,
    ReviewExtensionBody,
)
from app.services.hr.hr_deadline_service import (
    hr_list_deadlines,
    hr_list_extensions,
    hr_request_extension,
    hr_review_extension,
)

hr_deadline_router = APIRouter()


@hr_deadline_router.get(
    "/deadlines",
    response_model=DeadlineListResponse,
    summary="List all deadlines for HR user's cases",
)
async def api_hr_list_deadlines(
    search:        Optional[str] = Query(None),
    urgency:       Optional[str] = Query(None),
    deadline_type: Optional[str] = Query(None),
    db:            AsyncSession  = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> DeadlineListResponse:
    return await hr_list_deadlines(
        db            = db,
        hr_user_id    = current_user.user_id,
        search        = search,
        urgency       = urgency,
        deadline_type = deadline_type,
    )


@hr_deadline_router.get(
    "/deadlines/extensions",
    response_model=list[ExtensionRequestResponse],
    summary="List extension requests submitted by this HR user",
)
async def api_hr_list_extensions(
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> list[ExtensionRequestResponse]:
    return await hr_list_extensions(
        db         = db,
        hr_user_id = current_user.user_id,
    )


@hr_deadline_router.post(
    # NOTE: uses deadline_id (not application_id) — extensions are on a Deadline row
    "/deadlines/{deadline_id}/extension",
    response_model=ExtensionRequestResponse,
    status_code=201,
    summary="Submit an extension request for a specific deadline",
)
async def api_hr_request_extension(
    deadline_id: uuid.UUID,
    payload:     RequestExtensionBody,
    db:          AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> ExtensionRequestResponse:
    return await hr_request_extension(
        db             = db,
        hr_user_id     = current_user.user_id,
        deadline_id    = deadline_id,
        extension_days = payload.extension_days,
        reason         = payload.reason,
    )


@hr_deadline_router.patch(
    "/deadlines/extensions/{extension_id}",
    response_model=ExtensionRequestResponse,
    summary="Approve or deny an extension request",
)
async def api_hr_review_extension(
    extension_id: uuid.UUID,
    payload:      ReviewExtensionBody,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> ExtensionRequestResponse:
    return await hr_review_extension(
        db           = db,
        hr_user_id   = current_user.user_id,
        extension_id = extension_id,
        action       = payload.action,
        note         = payload.note,
    )