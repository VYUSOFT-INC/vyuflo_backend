# =============================================================================
# app/services/application_extra_service.py
#
# NEW service functions only — Comments + Deadlines (Screens 9, 10, 11)
# Your existing app/services/application_services.py is NOT touched.
#
# Reuses:
#   db_create, db_update, db_delete  — from your existing services.py
#   Application model                — ownership check
#   ApplicationComment, Deadline     — from visamodels.py
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.visamodels import (
    Application,
    ApplicationComment,
    Deadline,
    User,
)
from app.schemas.attorney.application_extra import (
    CommentAuthor,
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    CommentUpdate,
    DeadlineCreate,
    DeadlineListResponse,
    DeadlineResponse,
    DeadlineUpdate,
)
from app.services.services import db_create, db_delete, db_update


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _assert_application_access(
    db:      AsyncSession,
    app_id:  uuid.UUID,
    user_id: uuid.UUID,
) -> Application:
    """Verify application exists and the user owns it."""
    result = await db.execute(
        select(Application).where(Application.id == app_id)
    )
    app = result.scalars().first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {app_id} not found.",
        )
    if app.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this application.",
        )
    return app


def _build_comment_response(comment: ApplicationComment) -> CommentResponse:
    """Map ORM ApplicationComment → CommentResponse with nested author."""
    author = None
    if comment.author:
        author = CommentAuthor(
            id         = comment.author.id,
            first_name = comment.author.first_name,
            last_name  = comment.author.last_name,
            email      = comment.author.email,
        )
    return CommentResponse(
        id             = comment.id,
        application_id = comment.application_id,
        author_id      = comment.author_id,
        author         = author,
        body           = comment.body,
        visible_to     = comment.visible_to,
        is_pinned      = comment.is_pinned,
        pinned_by      = comment.pinned_by,
        pinned_at      = comment.pinned_at,
        is_edited      = comment.is_edited,
        edited_at      = comment.edited_at,
        is_deleted     = comment.is_deleted,
        created_at     = comment.created_at,
        updated_at     = comment.updated_at,
    )


def _build_deadline_response(deadline: Deadline) -> DeadlineResponse:
    return DeadlineResponse(
        id             = deadline.id,
        application_id = deadline.application_id,
        user_id        = deadline.user_id,
        title          = deadline.title,
        description    = deadline.description,
        due_date       = deadline.due_date,
        urgency        = deadline.urgency,
        deadline_type  = deadline.deadline_type,
        is_completed   = deadline.is_completed,
        completed_at   = deadline.completed_at,
        completed_by   = deadline.completed_by,
        is_dismissed   = deadline.is_dismissed,
        dismissed_at   = deadline.dismissed_at,
        created_at     = deadline.created_at,
        updated_at     = deadline.updated_at,
    )


# =============================================================================
# COMMENT SERVICES
# =============================================================================

async def list_comments(
    db:      AsyncSession,
    app_id:  uuid.UUID,
    user_id: uuid.UUID,
) -> CommentListResponse:
    """
    GET /applications/{id}/comments
    Returns all non-deleted comments, newest first, with author nested.
    """
    await _assert_application_access(db, app_id, user_id)

    stmt = (
        select(ApplicationComment)
        .options(joinedload(ApplicationComment.author))
        .where(
            ApplicationComment.application_id == app_id,
            ApplicationComment.is_deleted     == False,
        )
        .order_by(ApplicationComment.is_pinned.desc(), ApplicationComment.created_at.desc())
    )
    result   = await db.execute(stmt)
    comments = result.scalars().all()

    items = [_build_comment_response(c) for c in comments]
    return CommentListResponse(items=items, total=len(items))


async def create_comment(
    db:      AsyncSession,
    app_id:  uuid.UUID,
    user_id: uuid.UUID,
    payload: CommentCreate,
) -> CommentResponse:
    """
    POST /applications/{id}/comments
    """
    await _assert_application_access(db, app_id, user_id)

    comment = ApplicationComment(
        application_id = app_id,
        author_id      = user_id,
        body           = payload.body,
        visible_to     = payload.visible_to,
        is_pinned      = False,
        is_edited      = False,
        is_deleted     = False,
        created_by     = user_id,
    )
    comment = await db_create(db, comment)

    # Reload with author relationship
    result = await db.execute(
        select(ApplicationComment)
        .options(joinedload(ApplicationComment.author))
        .where(ApplicationComment.id == comment.id)
    )
    return _build_comment_response(result.scalars().first())


async def update_comment(
    db:         AsyncSession,
    app_id:     uuid.UUID,
    comment_id: uuid.UUID,
    user_id:    uuid.UUID,
    payload:    CommentUpdate,
) -> CommentResponse:
    """
    PATCH /applications/{id}/comments/{comment_id}
    Only the original author can edit their comment.
    """
    result = await db.execute(
        select(ApplicationComment)
        .options(joinedload(ApplicationComment.author))
        .where(ApplicationComment.id == comment_id)
    )
    comment = result.scalars().first()

    if not comment or comment.application_id != app_id:
        raise HTTPException(status_code=404, detail="Comment not found.")
    if comment.is_deleted:
        raise HTTPException(status_code=410, detail="Comment has been deleted.")
    if comment.author_id != user_id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments.")

    await db_update(db, ApplicationComment, comment_id, {
        "body":        payload.body,
        "is_edited":   True,
        "edited_at":   datetime.now(timezone.utc),
        "modified_by": user_id,
    })

    # Reload
    result = await db.execute(
        select(ApplicationComment)
        .options(joinedload(ApplicationComment.author))
        .where(ApplicationComment.id == comment_id)
    )
    return _build_comment_response(result.scalars().first())


async def delete_comment(
    db:         AsyncSession,
    app_id:     uuid.UUID,
    comment_id: uuid.UUID,
    user_id:    uuid.UUID,
) -> dict:
    """
    DELETE /applications/{id}/comments/{comment_id}
    Soft delete — sets is_deleted = True. Author or admin only.
    """
    result = await db.execute(
        select(ApplicationComment).where(ApplicationComment.id == comment_id)
    )
    comment = result.scalars().first()

    if not comment or comment.application_id != app_id:
        raise HTTPException(status_code=404, detail="Comment not found.")
    if comment.author_id != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments.")

    await db_update(db, ApplicationComment, comment_id, {
        "is_deleted":  True,
        "deleted_at":  datetime.now(timezone.utc),
        "modified_by": user_id,
    })
    return {"detail": "Comment deleted.", "comment_id": str(comment_id)}


async def pin_comment(
    db:         AsyncSession,
    app_id:     uuid.UUID,
    comment_id: uuid.UUID,
    user_id:    uuid.UUID,
) -> CommentResponse:
    """
    PATCH /applications/{id}/comments/{comment_id}/pin
    Toggles pin state. Anyone with access can pin/unpin.
    """
    result = await db.execute(
        select(ApplicationComment)
        .options(joinedload(ApplicationComment.author))
        .where(ApplicationComment.id == comment_id)
    )
    comment = result.scalars().first()

    if not comment or comment.application_id != app_id:
        raise HTTPException(status_code=404, detail="Comment not found.")
    if comment.is_deleted:
        raise HTTPException(status_code=410, detail="Comment has been deleted.")

    # Toggle
    new_pinned = not comment.is_pinned
    updates = {
        "is_pinned":   new_pinned,
        "pinned_by":   user_id if new_pinned else None,
        "pinned_at":   datetime.now(timezone.utc) if new_pinned else None,
        "modified_by": user_id,
    }
    await db_update(db, ApplicationComment, comment_id, updates)

    # Reload
    result = await db.execute(
        select(ApplicationComment)
        .options(joinedload(ApplicationComment.author))
        .where(ApplicationComment.id == comment_id)
    )
    return _build_comment_response(result.scalars().first())


# =============================================================================
# DEADLINE SERVICES
# =============================================================================

async def list_deadlines(
    db:      AsyncSession,
    app_id:  uuid.UUID,
    user_id: uuid.UUID,
) -> DeadlineListResponse:
    """
    GET /applications/{id}/deadlines
    Returns all deadlines for this application, ordered by due_date asc.
    """
    await _assert_application_access(db, app_id, user_id)

    stmt = (
        select(Deadline)
        .where(
            Deadline.application_id == app_id,
            Deadline.is_dismissed   == False,
        )
        .order_by(Deadline.due_date.asc())
    )
    result    = await db.execute(stmt)
    deadlines = result.scalars().all()

    items = [_build_deadline_response(d) for d in deadlines]
    return DeadlineListResponse(items=items, total=len(items))


async def create_deadline(
    db:      AsyncSession,
    app_id:  uuid.UUID,
    user_id: uuid.UUID,
    payload: DeadlineCreate,
) -> DeadlineResponse:
    """
    POST /applications/{id}/deadlines
    """
    await _assert_application_access(db, app_id, user_id)

    deadline = Deadline(
        application_id = app_id,
        user_id        = user_id,
        title          = payload.title,
        description    = payload.description,
        due_date       = payload.due_date,
        urgency        = payload.urgency,
        deadline_type  = payload.deadline_type,
        is_completed   = False,
        is_dismissed   = False,
        reminder_sent  = False,
        created_by     = user_id,
    )
    deadline = await db_create(db, deadline)
    return _build_deadline_response(deadline)


async def update_deadline(
    db:          AsyncSession,
    app_id:      uuid.UUID,
    deadline_id: uuid.UUID,
    user_id:     uuid.UUID,
    payload:     DeadlineUpdate,
) -> DeadlineResponse:
    """
    PATCH /applications/{id}/deadlines/{deadline_id}
    """
    result = await db.execute(
        select(Deadline).where(Deadline.id == deadline_id)
    )
    deadline = result.scalars().first()

    if not deadline or deadline.application_id != app_id:
        raise HTTPException(status_code=404, detail="Deadline not found.")
    if deadline.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields provided for update.")

    update_data["modified_by"] = user_id
    await db_update(db, Deadline, deadline_id, update_data)

    result = await db.execute(select(Deadline).where(Deadline.id == deadline_id))
    return _build_deadline_response(result.scalars().first())


async def delete_deadline(
    db:          AsyncSession,
    app_id:      uuid.UUID,
    deadline_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> dict:
    """
    DELETE /applications/{id}/deadlines/{deadline_id}
    Hard delete — deadlines have no audit trail requirement.
    """
    result = await db.execute(
        select(Deadline).where(Deadline.id == deadline_id)
    )
    deadline = result.scalars().first()

    if not deadline or deadline.application_id != app_id:
        raise HTTPException(status_code=404, detail="Deadline not found.")
    if deadline.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    await db_delete(db, Deadline, deadline_id)
    return {"detail": "Deadline deleted.", "deadline_id": str(deadline_id)}


async def complete_deadline(
    db:          AsyncSession,
    app_id:      uuid.UUID,
    deadline_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> DeadlineResponse:
    """
    PATCH /applications/{id}/deadlines/{deadline_id}/complete
    Toggles is_completed. Send again to undo.
    """
    result = await db.execute(
        select(Deadline).where(Deadline.id == deadline_id)
    )
    deadline = result.scalars().first()

    if not deadline or deadline.application_id != app_id:
        raise HTTPException(status_code=404, detail="Deadline not found.")
    if deadline.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    new_completed = not deadline.is_completed
    await db_update(db, Deadline, deadline_id, {
        "is_completed": new_completed,
        "completed_at": datetime.now(timezone.utc) if new_completed else None,
        "completed_by": user_id if new_completed else None,
        "modified_by":  user_id,
    })

    result = await db.execute(select(Deadline).where(Deadline.id == deadline_id))
    return _build_deadline_response(result.scalars().first())


async def dismiss_deadline(
    db:          AsyncSession,
    app_id:      uuid.UUID,
    deadline_id: uuid.UUID,
    user_id:     uuid.UUID,
) -> dict:
    """
    PATCH /applications/{id}/deadlines/{deadline_id}/dismiss
    Hides the deadline from the list (is_dismissed = True).
    """
    result = await db.execute(
        select(Deadline).where(Deadline.id == deadline_id)
    )
    deadline = result.scalars().first()

    if not deadline or deadline.application_id != app_id:
        raise HTTPException(status_code=404, detail="Deadline not found.")
    if deadline.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    await db_update(db, Deadline, deadline_id, {
        "is_dismissed": True,
        "dismissed_at": datetime.now(timezone.utc),
        "modified_by":  user_id,
    })
    return {"detail": "Deadline dismissed.", "deadline_id": str(deadline_id)}
