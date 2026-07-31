# src/api/messages/router.py
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.employee.message import (
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    MarkReadResponse,
    ThreadCreate,
    ThreadListResponse,
    ThreadResponse,
)
from app.services.employee.message_service import (
    create_thread,
    get_thread,
    list_messages,
    list_threads,
    mark_thread_read,
    send_message,
)

message_router = APIRouter()


# =============================================================================
# THREADS (Conversations)
# =============================================================================

@message_router.get(
    "/messages/conversations",
    response_model=ThreadListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all conversations for current user",
    description=(
        "Returns all message threads the current user participates in, "
        "sorted by most recent message. Powers the left panel of Screen 24."
    ),
)
async def api_list_threads(
    db:           AsyncSession = Depends(get_db),
    current_user: uuid.UUID    = Depends(get_current_user),
) -> ThreadListResponse:
    return await list_threads(db, current_user.user_id)


@message_router.post(
    "/messages/conversations",
    response_model=ThreadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation thread",
    description=(
        "Creates a direct (1-on-1) or group thread. "
        "For direct threads, returns existing thread if one already exists "
        "between the two users (idempotent)."
    ),
)
async def api_create_thread(
    payload:      ThreadCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: uuid.UUID    = Depends(get_current_user),
) -> ThreadResponse:
    return await create_thread(db, current_user.user_id, payload)


@message_router.get(
    "/messages/conversations/{thread_id}",
    response_model=ThreadResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single conversation thread",
)
async def api_get_thread(
    thread_id:    uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: uuid.UUID    = Depends(get_current_user),
) -> ThreadResponse:
    return await get_thread(db, thread_id, current_user.user_id)


# =============================================================================
# MESSAGES
# =============================================================================

from fastapi import Request
from starlette.datastructures import UploadFile as StarletteUploadFile

@message_router.post(
    "/messages/conversations/{thread_id}/attachments",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def api_send_file_message(
    thread_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> MessageResponse:
    form = await request.form()

    content = form.get("content")
    file = form.get("file") or form.get("attachment") or form.get("document")

    if content == "":
        content = None

    if not isinstance(file, StarletteUploadFile):
        file = None

    return await send_message(
        db=db,
        thread_id=thread_id,
        user_id=current_user.user_id,
        content=content,
        file=file,
    )


@message_router.post(
    "/messages/conversations/{thread_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
)
async def api_send_message(
    thread_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> MessageResponse:
    return await send_message(
        db=db,
        thread_id=thread_id,
        user_id=current_user.user_id,
        content=payload.content,
        file=None,
    )

@message_router.get(
    "/messages/conversations/{thread_id}/messages",
    response_model=MessageListResponse,
    status_code=status.HTTP_200_OK,
    summary="List messages in a conversation",
    description=(
        "Returns messages oldest-first (natural chat order). "
        "Supports pagination via limit/offset for loading older messages."
    ),
)
async def api_list_messages(
    thread_id:    uuid.UUID,
    limit:        int          = Query(50,  ge=1, le=200),
    offset:       int          = Query(0,   ge=0),
    db:           AsyncSession = Depends(get_db),
    current_user: uuid.UUID    = Depends(get_current_user),
) -> MessageListResponse:
    return await list_messages(db, thread_id, current_user.user_id, limit, offset)



# =============================================================================
# READ RECEIPTS
# =============================================================================

@message_router.patch(
    "/messages/conversations/{thread_id}/read",
    response_model=MarkReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all messages in a thread as read",
    description=(
        "Resets the current user's unread_count to 0 for this thread "
        "and marks all received messages as read. "
        "Called automatically when the user opens a conversation."
    ),
)
async def api_mark_read(
    thread_id:    uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: uuid.UUID    = Depends(get_current_user),
) -> MarkReadResponse:
    return await mark_thread_read(db, thread_id, current_user.user_id)