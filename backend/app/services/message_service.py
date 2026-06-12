# src/services/message_service.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.visamodels import (
    Message,
    MessageThread,
    MessageThreadParticipant,
    Document,
    DocumentType,
    User,
)
from app.schemas.message import (
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    ThreadCreate,
    ThreadListResponse,
    ThreadResponse,
    MarkReadResponse,
)
from app.services.services import db_create, db_update


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_size(kb: Optional[int]) -> Optional[str]:
    """Convert file_size_kb → '1.2 MB' or '340 KB'."""
    if not kb:
        return None
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB"
    return f"{kb} KB"


def _build_message_response(msg: Message) -> MessageResponse:
    """Map ORM Message → MessageResponse."""
    doc = getattr(msg, "attachment", None)
    return MessageResponse(
        id                    = msg.id,
        thread_id             = msg.thread_id,
        sender_id             = msg.sender_id,
        content               = msg.body if not msg.is_deleted else "This message was deleted",
        message_type          = msg.message_type,
        attachment_name       = doc.file_name          if doc else None,
        attachment_url        = f"/documents/{doc.id}/view" if doc else None,
        attachment_size       = _fmt_size(doc.file_size_kb) if doc else None,
        document_id           = doc.id                 if doc else None,
        call_duration_seconds = msg.call_duration_seconds,
        call_status           = msg.call_status,
        is_read               = msg.is_read,
        is_edited             = msg.is_edited,
        is_deleted            = msg.is_deleted,
        created_at            = msg.created_at,
        updated_at            = msg.updated_at,
    )


async def _get_participant_or_404(
    db:        AsyncSession,
    thread_id: uuid.UUID,
    user_id:   uuid.UUID,
) -> MessageThreadParticipant:
    """Verify user is a participant of this thread."""
    result = await db.execute(
        select(MessageThreadParticipant).where(
            MessageThreadParticipant.thread_id == thread_id,
            MessageThreadParticipant.user_id   == user_id,
            MessageThreadParticipant.left_at.is_(None),
        )
    )
    p = result.scalars().first()
    if not p:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this thread.",
        )
    return p


def _build_thread_response(
    thread:       MessageThread,
    current_user_id: uuid.UUID,
) -> ThreadResponse:
    """
    Map a MessageThread ORM object → ThreadResponse.
    For direct threads: exposes the OTHER participant's name/avatar/role.
    For group threads: exposes the group title.
    """
    participants = thread.participants or []

    # Find current user's participant row to get their unread count
    my_participant = next(
        (p for p in participants if p.user_id == current_user_id), None
    )
    unread_count = my_participant.unread_count if my_participant else 0

    if thread.thread_type == "direct":
        # Find the OTHER participant
        other = next(
            (p for p in participants if p.user_id != current_user_id), None
        )
        other_user: Optional[User] = getattr(other, "user", None) if other else None
        participant_name = (
            f"{other_user.first_name} {other_user.last_name}".strip()
            if other_user else "Unknown"
        )
        avatar_url       = getattr(other_user, "profile_picture_url", None) if other_user else None
        participant_role = other.participant_role if other else None
        is_online        = other.is_online if other else False
        participant_id   = other.user_id if other else None
    else:
        # Group thread — use title
        participant_name = thread.title or "Group"
        avatar_url       = None
        participant_role = None
        is_online        = False
        participant_id   = None

    return ThreadResponse(
        id               = thread.id,
        thread_type      = thread.thread_type,
        title            = thread.title,
        application_id   = thread.application_id,
        is_archived      = my_participant.is_archived if my_participant else thread.is_archived,
        participant_id   = participant_id,
        participant_name = participant_name,
        participant_role = participant_role,
        avatar_url       = avatar_url,
        is_online        = is_online,
        last_message     = thread.last_message_preview,
        last_message_at  = thread.last_message_at,
        unread_count     = unread_count,
        created_at       = thread.created_at,
    )


# =============================================================================
# THREAD SERVICES
# =============================================================================

async def list_threads(
    db:      AsyncSession,
    user_id: uuid.UUID,
) -> ThreadListResponse:
    """
    GET /messages/conversations
    Returns all threads the current user participates in,
    sorted by last_message_at desc (most recent first).
    """
    result = await db.execute(
        select(MessageThread)
        .join(
            MessageThreadParticipant,
            MessageThreadParticipant.thread_id == MessageThread.id,
        )
        .where(
            MessageThreadParticipant.user_id  == user_id,
            MessageThreadParticipant.left_at.is_(None),
            MessageThread.is_active == True,
        )
        .options(
            selectinload(MessageThread.participants)
            .joinedload(MessageThreadParticipant.user)
        )
        .order_by(MessageThread.last_message_at.desc().nullslast())
    )
    threads = result.scalars().unique().all()

    items = [_build_thread_response(t, user_id) for t in threads]
    return ThreadListResponse(items=items, total=len(items))


async def create_thread(
    db:      AsyncSession,
    user_id: uuid.UUID,
    payload: ThreadCreate,
) -> ThreadResponse:
    """
    POST /messages/conversations
    Create a new direct or group thread.
    For direct threads, checks if a thread already exists between the two users.
    """
    # ── Guard: direct thread must have exactly 1 other participant ────────────
    if payload.thread_type == "direct":
        if len(payload.participant_ids) != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Direct threads require exactly 1 other participant.",
            )

        other_id = payload.participant_ids[0]

        # Check if a direct thread already exists between these two users
        existing = await db.execute(
            select(MessageThread)
            .join(MessageThreadParticipant,
                  MessageThreadParticipant.thread_id == MessageThread.id)
            .where(
                MessageThread.thread_type == "direct",
                MessageThread.is_active == True,
                MessageThreadParticipant.user_id == user_id,
                MessageThreadParticipant.left_at.is_(None),
            )
        )
        for thread in existing.scalars().all():
            # Check if other user is also in this thread
            check = await db.execute(
                select(MessageThreadParticipant).where(
                    MessageThreadParticipant.thread_id == thread.id,
                    MessageThreadParticipant.user_id   == other_id,
                    MessageThreadParticipant.left_at.is_(None),
                )
            )
            if check.scalars().first():
                # Thread already exists — return it
                result = await db.execute(
                    select(MessageThread)
                    .where(MessageThread.id == thread.id)
                    .options(
                        selectinload(MessageThread.participants)
                        .joinedload(MessageThreadParticipant.user)
                    )
                )
                return _build_thread_response(result.scalars().first(), user_id)

    elif payload.thread_type == "group" and not payload.title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Group threads require a title.",
        )

    # ── Fetch roles for all participants ──────────────────────────────────────
    all_user_ids = [user_id] + list(payload.participant_ids)
    users_result = await db.execute(
        select(User).where(User.id.in_(all_user_ids))
    )
    users_map = {u.id: u for u in users_result.scalars().all()}

    # ── Create thread ─────────────────────────────────────────────────────────
    thread = MessageThread(
        thread_type    = payload.thread_type,
        title          = payload.title,
        application_id = payload.application_id,
        is_active      = True,
        created_by     = user_id,
    )
    thread = await db_create(db, thread)

    # ── Create participant rows ────────────────────────────────────────────────
    # Determine role from User model
    def _get_role(u: Optional[User]) -> str:
        if not u:
            return "employee"
        roles = [r.name for r in getattr(u, "roles", [])]
        for r in ["attorney", "hr", "support", "admin"]:
            if r in roles:
                return r
        return "employee"

    for uid in all_user_ids:
        u = users_map.get(uid)
        participant = MessageThreadParticipant(
            thread_id        = thread.id,
            user_id          = uid,
            participant_role = _get_role(u),
            is_online        = False,
            unread_count     = 0,
            created_by       = user_id,
        )
        await db_create(db, participant)

    # ── Optionally send first message ─────────────────────────────────────────
    if payload.initial_message:
        msg = Message(
            thread_id    = thread.id,
            sender_id    = user_id,
            body         = payload.initial_message,
            message_type = "text",
            is_read      = False,
            created_by   = user_id,
        )
        msg = await db_create(db, msg)
        await db_update(db, MessageThread, thread.id, {
            "last_message_preview": payload.initial_message[:200],
            "last_message_at":      msg.created_at,
            "modified_by":          user_id,
        })

    # Reload with relationships
    result = await db.execute(
        select(MessageThread)
        .where(MessageThread.id == thread.id)
        .options(
            selectinload(MessageThread.participants)
            .joinedload(MessageThreadParticipant.user)
        )
    )
    return _build_thread_response(result.scalars().first(), user_id)


async def get_thread(
    db:        AsyncSession,
    thread_id: uuid.UUID,
    user_id:   uuid.UUID,
) -> ThreadResponse:
    """GET /messages/conversations/:id"""
    await _get_participant_or_404(db, thread_id, user_id)

    result = await db.execute(
        select(MessageThread)
        .where(MessageThread.id == thread_id)
        .options(
            selectinload(MessageThread.participants)
            .joinedload(MessageThreadParticipant.user)
        )
    )
    thread = result.scalars().first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found.")

    return _build_thread_response(thread, user_id)


# =============================================================================
# MESSAGE SERVICES
# =============================================================================

async def list_messages(
    db:        AsyncSession,
    thread_id: uuid.UUID,
    user_id:   uuid.UUID,
    limit:     int = 50,
    offset:    int = 0,
) -> MessageListResponse:
    """
    GET /messages/conversations/:id/messages
    Returns messages oldest-first (natural chat order).
    Excludes soft-deleted messages body but keeps the row.
    """
    await _get_participant_or_404(db, thread_id, user_id)

    result = await db.execute(
        select(Message)
        .where(
            Message.thread_id  == thread_id,
        )
        .options(joinedload(Message.attachment))
        .order_by(Message.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    msgs = result.scalars().all()

    # Count total (for pagination)
    count_result = await db.execute(
        select(func.count()).where(Message.thread_id == thread_id)
    )
    total = count_result.scalar_one()

    return MessageListResponse(
        items=[_build_message_response(m) for m in msgs],
        total=total,
    )


async def send_message(
    db:        AsyncSession,
    thread_id: uuid.UUID,
    user_id:   uuid.UUID,
    content:   Optional[str],
    file:      Optional[UploadFile] = None,
) -> MessageResponse:
    """
    POST /messages/conversations/:id/messages
    Handles both plain text and file attachments.
    """
    await _get_participant_or_404(db, thread_id, user_id)

    if not content and not file:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message must have content or a file attachment.",
        )

    document_id  = None
    message_type = "text"

    # ── Handle file attachment ────────────────────────────────────────────────
    if file:
        message_type = "file_attachment"
        import os
        from app.services.services import db_create as _create

        # Find or create DocumentType for "message_attachment"
        doc_type_result = await db.execute(
            select(DocumentType).where(DocumentType.name == "message_attachment")
        )
        doc_type = doc_type_result.scalars().first()
        if not doc_type:
            doc_type = DocumentType(
                name        = "message_attachment",
                category    = "other",
                description = "File sent via secure messaging",
                created_by  = user_id,
            )
            doc_type = await db_create(db, doc_type)

        file_bytes   = await file.read()
        file_size_kb = len(file_bytes) // 1024
        ext          = (file.filename or "file").rsplit(".", 1)[-1].lower()
        file_format  = ext if ext in ("pdf", "jpg", "jpeg", "png", "docx") else "pdf"

        storage_path = f"uploads/{user_id}/messages/{file.filename}"
        os.makedirs(os.path.dirname(f"./{storage_path}"), exist_ok=True)
        with open(f"./{storage_path}", "wb") as f_out:
            f_out.write(file_bytes)

        doc = Document(
            user_id          = user_id,
            document_type_id = doc_type.id,
            file_name        = file.filename,
            file_path        = storage_path,
            file_size_kb     = file_size_kb,
            file_format      = file_format,
            status           = "uploaded",
            ocr_status       = "not_started",
            version          = 1,
            is_draft         = False,
            created_by       = user_id,
        )
        doc = await db_create(db, doc)
        document_id = doc.id

    # ── Create message row ────────────────────────────────────────────────────
    msg = Message(
        thread_id    = thread_id,
        sender_id    = user_id,
        body         = content,
        message_type = message_type,
        document_id  = document_id,
        is_read      = False,
        created_by   = user_id,
    )
    msg = await db_create(db, msg)

    # ── Update thread's last message preview ──────────────────────────────────
    preview = content[:200] if content else f"📎 {file.filename}" if file else ""
    await db_update(db, MessageThread, thread_id, {
        "last_message_preview": preview,
        "last_message_at":      msg.created_at,
        "modified_by":          user_id,
    })

    # ── Increment unread count for all OTHER participants ─────────────────────
    participants_result = await db.execute(
        select(MessageThreadParticipant).where(
            MessageThreadParticipant.thread_id == thread_id,
            MessageThreadParticipant.user_id   != user_id,
            MessageThreadParticipant.left_at.is_(None),
        )
    )
    for p in participants_result.scalars().all():
        await db_update(db, MessageThreadParticipant, p.id, {
            "unread_count": p.unread_count + 1,
            "modified_by":  user_id,
        })

    # Reload with attachment relationship
    result = await db.execute(
        select(Message)
        .where(Message.id == msg.id)
        .options(joinedload(Message.attachment))
    )
    return _build_message_response(result.scalars().first())


async def mark_thread_read(
    db:        AsyncSession,
    thread_id: uuid.UUID,
    user_id:   uuid.UUID,
) -> MarkReadResponse:
    """
    PATCH /messages/conversations/:id/read
    Resets unread_count to 0 for the current user in this thread.
    Also marks all messages in thread as read.
    """
    participant = await _get_participant_or_404(db, thread_id, user_id)

    now = datetime.now(timezone.utc)

    # Reset participant's unread count
    await db_update(db, MessageThreadParticipant, participant.id, {
        "unread_count": 0,
        "last_read_at": now,
        "modified_by":  user_id,
    })

    # Mark all unread messages in this thread as read
    from sqlalchemy import update
    await db.execute(
        update(Message)
        .where(
            Message.thread_id == thread_id,
            Message.sender_id != user_id,
            Message.is_read   == False,
        )
        .values(is_read=True, read_at=now)
    )

    return MarkReadResponse(thread_id=thread_id, unread_count=0)