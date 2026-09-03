# =============================================================================
# app/services/screen12_service.py
# Screen 12 — Secure Messages
#
# Functions:
#   service_list_message_templates()    → GET  /messages/templates
#   service_create_message_template()   → POST /messages/templates
#   service_update_message_template()   → PATCH /messages/templates/{id}
#   service_delete_message_template()   → DELETE /messages/templates/{id}
#
# Enhanced thread functions (replace in app/services/message_service.py):
#   service_list_threads()              → GET /messages/conversations
#   service_get_thread()                → GET /messages/conversations/{id}
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.visamodels import (
    Application,
    Message,
    MessageThread,
    MessageThreadParticipant,
    MessageTemplate,
    Role,          #new
    User,          #new
    UserRole,      #new
    VisaType,
)


# =============================================================================
# MESSAGE TEMPLATES
# =============================================================================

async def service_list_message_templates(
    db:       AsyncSession,
    category: Optional[str] = None,
) -> dict:
    """
    Returns all active templates ordered by sort_order.
    Optionally filtered by category.
    Powers the chip bar on Screen 12 compose box.
    """
    query = (
        select(MessageTemplate)
        .where(MessageTemplate.is_active == True)  # noqa: E712
        .order_by(MessageTemplate.sort_order.asc())
    )
    if category:
        query = query.where(MessageTemplate.category == category)

    result    = await db.execute(query)
    templates = result.scalars().all()
    return {"items": templates, "total": len(templates)}


async def service_create_message_template(
    db:         AsyncSession,
    name:       str,
    body:       str,
    created_by: uuid.UUID,
    category:   Optional[str] = None,
    sort_order: int            = 0,
    is_active:  bool           = True,
) -> MessageTemplate:
    """Creates a new reply template chip (admin only)."""
    template = MessageTemplate(
        id=uuid.uuid4(),
        name=name,
        body=body,
        category=category,
        sort_order=sort_order,
        is_active=is_active,
        created_by=created_by,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def service_update_message_template(
    db:          AsyncSession,
    template_id: uuid.UUID,
    modified_by: uuid.UUID,
    name:        Optional[str]  = None,
    body:        Optional[str]  = None,
    category:    Optional[str]  = None,
    sort_order:  Optional[int]  = None,
    is_active:   Optional[bool] = None,
) -> MessageTemplate:
    """Partial update — only provided fields are written (admin only)."""
    result   = await db.execute(
        select(MessageTemplate).where(MessageTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Message template not found.")

    if name       is not None: template.name       = name
    if body       is not None: template.body       = body
    if category   is not None: template.category   = category
    if sort_order is not None: template.sort_order = sort_order
    if is_active  is not None: template.is_active  = is_active

    template.modified_by = modified_by
    template.updated_at  = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(template)
    return template


async def service_delete_message_template(
    db:          AsyncSession,
    template_id: uuid.UUID,
    deleted_by:  uuid.UUID,
) -> dict:
    """Soft-delete — sets is_active=False (admin only)."""
    result   = await db.execute(
        select(MessageTemplate).where(MessageTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Message template not found.")

    template.is_active   = False
    template.modified_by = deleted_by
    template.updated_at  = datetime.now(timezone.utc)

    await db.commit()
    return {"message": "Template deactivated.", "id": str(template_id)}


# =============================================================================
# ENHANCED THREAD FUNCTIONS
# Drop-in replacements for list_threads() and get_thread() in
# app/services/message_service.py.
# All other functions in that file remain unchanged.
# =============================================================================

async def service_list_threads(
    db:      AsyncSession,
    user_id: uuid.UUID,
    search:  Optional[str] = None,
) -> dict:
    """
    List all threads the current user participates in, newest first.

    Enhancements over original:
      • search  — matches thread title, last_message_preview, or application_number
      • Each thread carries 4 new enrichment attributes:
            _action_required  (message_threads.action_required)
            _thread_status    (message_threads.thread_status)
            _case_number      (Application.application_number)
            _visa_type_code   (VisaType.code)
    """
    # ── thread IDs this user is part of ──────────────────────────────────────
    part_q  = await db.execute(
        select(MessageThreadParticipant.thread_id)
        .where(
            MessageThreadParticipant.user_id == user_id,
            MessageThreadParticipant.left_at.is_(None),
        )
    )
    thread_ids = [row[0] for row in part_q.all()]
    if not thread_ids:
        return {"items": [], "total": 0, "unread_total": 0}

    # ── base query ────────────────────────────────────────────────────────────
    query = (
        select(MessageThread)
        .options(
            selectinload(MessageThread.participants)
            .selectinload(MessageThreadParticipant.user),
        )
        .where(
            MessageThread.id.in_(thread_ids),
            MessageThread.is_active == True,  # noqa: E712
        )
    )

    # ── search filter ─────────────────────────────────────────────────────────
    if search:
        term     = f"%{search}%"
        app_subq = select(Application.id).where(
            Application.application_number.ilike(term)
        )
        query = query.where(
            or_(
                MessageThread.title.ilike(term),
                MessageThread.last_message_preview.ilike(term),
                MessageThread.application_id.in_(app_subq),
            )
        )

    query   = query.order_by(MessageThread.last_message_at.desc().nullslast())
    result  = await db.execute(query)
    threads = result.scalars().all()

    # ── enrich each thread ────────────────────────────────────────────────────
    enriched = []
    for thread in threads:
        case_number = visa_type_code = None

        if thread.application_id:
            app_row = await db.execute(
                select(Application.application_number, VisaType.code)
                .join(VisaType, VisaType.id == Application.visa_type_id)
                .where(Application.id == thread.application_id)
            )
            row = app_row.one_or_none()
            if row:
                case_number, visa_type_code = row

        # current user's unread count
        unread = next(
            (p.unread_count for p in thread.participants if p.user_id == user_id),
            0,
        )

        # attach temp attributes for schema serialisation
        thread._case_number     = case_number
        thread._visa_type_code  = visa_type_code
        thread._unread_count    = unread
        # getattr guard keeps it working before migration is applied
        thread._action_required = getattr(thread, "action_required", False)
        thread._thread_status   = getattr(thread, "thread_status", "active")

        enriched.append(thread)

    return {
        "items":        enriched,
        "total":        len(enriched),
        "unread_total": sum(t._unread_count for t in enriched),
    }


async def service_get_thread(
    db:        AsyncSession,
    thread_id: uuid.UUID,
    user_id:   uuid.UUID,
) -> MessageThread:
    """
    Get single thread — validates participation, enriches with case data.
    Drop-in replacement for get_thread() in message_service.py.
    """
    # verify user is a participant
    part = await db.execute(
        select(MessageThreadParticipant).where(
            MessageThreadParticipant.thread_id == thread_id,
            MessageThreadParticipant.user_id   == user_id,
            MessageThreadParticipant.left_at.is_(None),
        )
    )
    if not part.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You are not a participant in this conversation.")

    result = await db.execute(
        select(MessageThread)
        .options(
            selectinload(MessageThread.participants)
            .selectinload(MessageThreadParticipant.user),
        )
        .where(MessageThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Conversation not found.")

    # enrich with case data
    case_number = visa_type_code = None
    if thread.application_id:
        app_row = await db.execute(
            select(Application.application_number, VisaType.code)
            .join(VisaType, VisaType.id == Application.visa_type_id)
            .where(Application.id == thread.application_id)
        )
        row = app_row.one_or_none()
        if row:
            case_number, visa_type_code = row

    thread._case_number     = case_number
    thread._visa_type_code  = visa_type_code
    thread._action_required = getattr(thread, "action_required", False)
    thread._thread_status   = getattr(thread, "thread_status", "active")

    return thread


# =============================================================================
# STAFF SEARCH — "+ New message" compose box
# =============================================================================

async def service_search_staff(
    db:      AsyncSession,
    user_id: uuid.UUID,
    query:   str,
    limit:   int = 20,
):   #new — entire function
    """
    Search for someone to start a new conversation with, by name or email.
    Excludes the current user. Returns each match's role (from user_roles/
    roles) so the frontend can show "HR", "Attorney", etc. next to the name.

    NOTE ON SCOPE: this intentionally does NOT restrict results to only
    people the attorney shares a case with — create_thread() in
    message_service.py already accepts any valid user_id today, so this
    search matches that same (currently unscoped) behavior rather than
    introducing a stricter rule the rest of the messaging feature doesn't
    enforce. If you want to restrict messaging to case-linked people only,
    that's a bigger, deliberate change — flag it and we'll scope it properly.
    """
    search_term = f"%{query.strip()}%"

    result = await db.execute(
        select(User, Role.name)
        .outerjoin(UserRole, UserRole.user_id == User.id)
        .outerjoin(Role, Role.id == UserRole.role_id)
        .where(
            User.id != user_id,
            User.is_active == True,
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.email.ilike(search_term),
            ),
        )
        .limit(limit)
    )
    rows = result.all()

    items = []
    seen_user_ids = set()
    for user, role_name in rows:
        if user.id in seen_user_ids:
            continue   # a user can have more than one role row — keep first match only
        seen_user_ids.add(user.id)
        items.append({
            "id":         user.id,   #new — duplicate of user_id
            "user_id":    user.id,
            "first_name": user.first_name or "",   #new
            "last_name":  user.last_name or "",    #new
            "full_name":  f"{user.first_name} {user.last_name}".strip() or user.email,
            "email":      user.email,
            "role":       role_name,
            "avatar_url": getattr(user, "profile_picture_url", None),
        })

    return {"items": items, "total": len(items)}


async def service_list_users_by_roles(
    db:      AsyncSession,
    user_id: uuid.UUID,
    roles:   list[str],
):   #new — entire function
    """
    GET /api/v1/users?roles=hr,attorney,support

    This is the endpoint the "New Conversation" search box actually calls —
    it fetches everyone in the given roles ONCE, and the frontend filters
    that list locally as the person types (no text query sent to the
    backend). Excludes the current user. Role names are matched
    case-insensitively against app.models.visamodels.Role.name.
    """
    normalized_roles = [r.strip().lower() for r in roles if r.strip()]

    result = await db.execute(
        select(User, Role.name)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            User.id != user_id,
            User.is_active == True,
            func.lower(Role.name).in_(normalized_roles),
        )
    )
    rows = result.all()

    items = []
    seen_user_ids = set()
    for user, role_name in rows:
        if user.id in seen_user_ids:
            continue
        seen_user_ids.add(user.id)
        items.append({
            "id":         user.id,   #new — duplicate of user_id
            "user_id":    user.id,
            "first_name": user.first_name or "",   #new
            "last_name":  user.last_name or "",    #new
            "full_name":  f"{user.first_name} {user.last_name}".strip() or user.email,
            "email":      user.email,
            "role":       role_name,
            "avatar_url": getattr(user, "profile_picture_url", None),
        })

    return {"items": items, "total": len(items)}