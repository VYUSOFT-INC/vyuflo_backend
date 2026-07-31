# =============================================================================
# app/routers/application_extra.py
#
# NEW endpoints only — Comments + Deadlines (Screens 9, 10, 11)
# Your existing app/routers/application.py is NOT touched.
#
# Register in main.py alongside your existing router:
#
#   from app.routers.application_extra import application_extra_router
#   app.include_router(application_extra_router, prefix="/api/v1", tags=["Applications"])
# =============================================================================

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.schemas.attorney.application_extra import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    CommentUpdate,
    DeadlineCreate,
    DeadlineListResponse,
    DeadlineResponse,
    DeadlineUpdate,
)
from app.services.attorney.application_extra_service import (
    # comments
    complete_deadline,
    create_comment,
    create_deadline,
    delete_comment,
    delete_deadline,
    dismiss_deadline,
    list_comments,
    list_deadlines,
    pin_comment,
    update_comment,
    update_deadline,
)

application_extra_router = APIRouter()


# =============================================================================
# COMMENTS  —  /applications/{id}/comments
# =============================================================================

@application_extra_router.get(
    "/applications/{application_id}/comments",
    response_model=CommentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all comments/notes for an application (Screen 11)",
    description=(
        "Returns all non-deleted comments ordered by pinned first, "
        "then newest. Includes nested author info."
    ),
)
async def api_list_comments(
    application_id: uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> CommentListResponse:
    return await list_comments(db, application_id, current_user.user_id)


@application_extra_router.post(
    "/applications/{application_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment/note to an application",
)
async def api_create_comment(
    application_id: uuid.UUID,
    payload:        CommentCreate,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> CommentResponse:
    return await create_comment(db, application_id, current_user.user_id, payload)


@application_extra_router.patch(
    "/applications/{application_id}/comments/{comment_id}",
    response_model=CommentResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit a comment (author only)",
)
async def api_update_comment(
    application_id: uuid.UUID,
    comment_id:     uuid.UUID,
    payload:        CommentUpdate,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> CommentResponse:
    return await update_comment(
        db, application_id, comment_id, current_user.user_id, payload
    )


@application_extra_router.delete(
    "/applications/{application_id}/comments/{comment_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a comment (author only)",
)
async def api_delete_comment(
    application_id: uuid.UUID,
    comment_id:     uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> dict:
    return await delete_comment(
        db, application_id, comment_id, current_user.user_id
    )


@application_extra_router.patch(
    "/applications/{application_id}/comments/{comment_id}/pin",
    response_model=CommentResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle pin state on a comment",
    description="Pinned comments float to the top of the list.",
)
async def api_pin_comment(
    application_id: uuid.UUID,
    comment_id:     uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> CommentResponse:
    return await pin_comment(
        db, application_id, comment_id, current_user.user_id
    )


# =============================================================================
# DEADLINES  —  /applications/{id}/deadlines
# =============================================================================

@application_extra_router.get(
    "/applications/{application_id}/deadlines",
    response_model=DeadlineListResponse,
    status_code=status.HTTP_200_OK,
    summary="List deadlines for an application (Screen 11)",
    description="Returns all non-dismissed deadlines ordered by due_date ascending.",
)
async def api_list_deadlines(
    application_id: uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> DeadlineListResponse:
    return await list_deadlines(db, application_id, current_user.user_id)


@application_extra_router.post(
    "/applications/{application_id}/deadlines",
    response_model=DeadlineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a deadline for an application",
)
async def api_create_deadline(
    application_id: uuid.UUID,
    payload:        DeadlineCreate,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> DeadlineResponse:
    return await create_deadline(db, application_id, current_user.user_id, payload)


@application_extra_router.patch(
    "/applications/{application_id}/deadlines/{deadline_id}",
    response_model=DeadlineResponse,
    status_code=status.HTTP_200_OK,
    summary="Update deadline title, date, urgency, or type",
)
async def api_update_deadline(
    application_id: uuid.UUID,
    deadline_id:    uuid.UUID,
    payload:        DeadlineUpdate,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> DeadlineResponse:
    return await update_deadline(
        db, application_id, deadline_id, current_user.user_id, payload
    )


@application_extra_router.delete(
    "/applications/{application_id}/deadlines/{deadline_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a deadline",
)
async def api_delete_deadline(
    application_id: uuid.UUID,
    deadline_id:    uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> dict:
    return await delete_deadline(
        db, application_id, deadline_id, current_user.user_id
    )


@application_extra_router.patch(
    "/applications/{application_id}/deadlines/{deadline_id}/complete",
    response_model=DeadlineResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle deadline complete / incomplete",
    description="Call again on a completed deadline to undo.",
)
async def api_complete_deadline(
    application_id: uuid.UUID,
    deadline_id:    uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> DeadlineResponse:
    return await complete_deadline(
        db, application_id, deadline_id, current_user.user_id
    )


@application_extra_router.patch(
    "/applications/{application_id}/deadlines/{deadline_id}/dismiss",
    status_code=status.HTTP_200_OK,
    summary="Dismiss a deadline (hides it from the list)",
)
async def api_dismiss_deadline(
    application_id: uuid.UUID,
    deadline_id:    uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> dict:
    return await dismiss_deadline(
        db, application_id, deadline_id, current_user.user_id
    )
