# =============================================================================
# app/services/help_service.py
#
# NEW service functions for Lawyer Help & Support (Screens 28–36).
# Your existing app/services/admin/admin_support_service.py is NOT touched.
#
# Reuses from admin_support_service.py:
#   service_list_articles()  — imported directly, called with same args
#   service_get_article()    — imported directly
#   service_create_ticket()  — imported directly
# =============================================================================

from __future__ import annotations

import uuid
import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.visamodels import (
    Notification,
    SupportTicket,
    SupportTicketReply,
)
from app.schemas.attorney.help import (
    NotificationListResponse,
    NotificationResponse,
    TicketCreate,
    TicketDetailResponse,
    TicketListResponse,
    TicketReplyCreate,
    TicketReplyResponse,
    TicketSummaryResponse,
)
# Reuse admin article service — same logic, no duplication
from app.services.admin.admin_support_service import (
    service_get_article,
    service_list_articles,
)
from app.services.employee.services import db_create, db_update


# =============================================================================
# ARTICLES  (Screens 30, 31) — fully delegated to existing admin service
# =============================================================================

async def help_list_articles(
    db:           AsyncSession,
    page:         int           = 1,
    limit:        int           = 10,
    category:     Optional[str] = None,
    search:       Optional[str] = None,
    featured:     Optional[bool] = None,
    article_type: Optional[str] = None,
):
    """
    Screen 30 — Search Results:  call with search="..."
    Screen 31 — Support Resources: call with article_type or category
    Delegates entirely to existing admin service — zero duplication.
    """
    return await service_list_articles(
        db           = db,
        page         = page,
        limit        = limit,
        category     = category,
        search       = search,
        featured     = featured,
        article_type = article_type,
    )


async def help_get_article(db: AsyncSession, article_id: uuid.UUID):
    """
    Screen 31 — article detail / expanded view.
    Delegates to existing admin service — increments view_count.
    """
    return await service_get_article(db, article_id)


# =============================================================================
# TICKETS  (Screens 32, 33, 34, 35)
# =============================================================================

async def help_create_ticket(
    db:         AsyncSession,
    user_id:    uuid.UUID,
    payload:    TicketCreate,
) -> TicketDetailResponse:
    """
    Screen 32 — Submit Support Ticket.
    Creates ticket and returns detail shape (used by Screen 35 confirmation).
    """
    from app.core.exceptions import BadRequestException
    from app.schemas.admin.admin_support import TicketCreate as AdminTicketCreate

    # Reuse admin create service
    from app.services.admin.admin_support_service import service_create_ticket

    admin_payload = AdminTicketCreate(
        subject  = payload.subject,
        body     = payload.body,
        category = payload.category,
        priority = payload.priority,
    )
    ticket = await service_create_ticket(db, admin_payload, user_id)

    # If application_id provided, link it
    if payload.application_id:
        await db_update(db, SupportTicket, ticket.id, {
            "application_id": payload.application_id,
            "modified_by":    user_id,
        })

    # Return full detail shape (Screen 35 shows this immediately after submit)
    return TicketDetailResponse(
        id             = ticket.id,
        ticket_number  = ticket.ticket_number,
        subject        = ticket.subject,
        body           = payload.body,
        category       = ticket.category,
        priority       = ticket.priority,
        status         = ticket.status,
        application_id = payload.application_id,
        created_at     = ticket.created_at,
        updated_at     = ticket.created_at,
        replies        = [],
    )


async def help_list_my_tickets(
    db:       AsyncSession,
    user_id:  uuid.UUID,
    status_filter:   Optional[str] = None,
    category_filter: Optional[str] = None,
    page:     int = 1,
    limit:    int = 20,
) -> TicketListResponse:
    """
    Screen 33 — My Tickets.
    Returns only tickets submitted by this lawyer.
    """
    base_filters = [SupportTicket.user_id == user_id]

    if status_filter:
        base_filters.append(SupportTicket.status == status_filter)
    if category_filter:
        base_filters.append(SupportTicket.category == category_filter)

    # Count total
    total = (await db.execute(
        select(func.count()).select_from(SupportTicket).where(and_(*base_filters))
    )).scalar_one()

    # Status badge counts (always unfiltered by status)
    counts_stmt = select(
        SupportTicket.status,
        func.count().label("cnt"),
    ).where(SupportTicket.user_id == user_id).group_by(SupportTicket.status)
    count_rows = (await db.execute(counts_stmt)).all()
    counts = {row.status: row.cnt for row in count_rows}

    # Fetch page
    offset = (page - 1) * limit
    rows = (await db.execute(
        select(SupportTicket)
        .where(and_(*base_filters))
        .order_by(SupportTicket.created_at.desc())
        .offset(offset)
        .limit(limit)
    )).scalars().all()

    # Per-ticket reply count
    ticket_ids = [t.id for t in rows]
    reply_counts: dict[uuid.UUID, int] = {}
    if ticket_ids:
        rc_rows = (await db.execute(
            select(
                SupportTicketReply.ticket_id,
                func.count().label("cnt"),
            ).where(SupportTicketReply.ticket_id.in_(ticket_ids))
            .group_by(SupportTicketReply.ticket_id)
        )).all()
        reply_counts = {r.ticket_id: r.cnt for r in rc_rows}

    items = [
        TicketSummaryResponse(
            id            = t.id,
            ticket_number = t.ticket_number,
            subject       = t.subject,
            category      = t.category,
            priority      = t.priority,
            status        = t.status,
            reply_count   = reply_counts.get(t.id, 0),
            created_at    = t.created_at,
            updated_at    = t.updated_at,
        )
        for t in rows
    ]

    return TicketListResponse(
        items       = items,
        total       = total,
        open        = counts.get("open",        0),
        in_progress = counts.get("in_progress", 0),
        resolved    = counts.get("resolved",    0),
    )


async def help_get_ticket_detail(
    db:        AsyncSession,
    user_id:   uuid.UUID,
    ticket_id: uuid.UUID,
) -> TicketDetailResponse:
    """
    Screen 34 — Ticket Detail with full reply thread.
    Screen 35 — also used to load just-submitted ticket confirmation.
    Ownership check: lawyer can only see their own tickets.
    """
    result = await db.execute(
        select(SupportTicket)
        .options(joinedload(SupportTicket.replies))
        .where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalars().first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    if ticket.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Filter out internal notes from user-facing view
    visible_replies = [
        r for r in (ticket.replies or [])
        if not r.is_internal_note
    ]

    replies = [
        TicketReplyResponse(
            id               = r.id,
            ticket_id        = r.ticket_id,
            sender_id        = r.sender_id,
            sender_type      = r.sender_type,
            body             = r.body,
            is_read          = r.is_read,
            is_internal_note = r.is_internal_note,
            created_at       = r.created_at,
        )
        for r in visible_replies
    ]

    return TicketDetailResponse(
        id             = ticket.id,
        ticket_number  = ticket.ticket_number,
        subject        = ticket.subject,
        body           = ticket.body,
        category       = ticket.category,
        priority       = ticket.priority,
        status         = ticket.status,
        application_id = ticket.application_id,
        created_at     = ticket.created_at,
        updated_at     = ticket.updated_at,
        replies        = replies,
    )


async def help_reply_to_ticket(
    db:        AsyncSession,
    user_id:   uuid.UUID,
    ticket_id: uuid.UUID,
    payload:   TicketReplyCreate,
) -> TicketReplyResponse:
    """
    Screen 34 — lawyer replies to their own ticket.
    Sets ticket status → in_progress if it was open.
    """
    # Ownership check
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    if ticket.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if ticket.status in ("resolved", "closed"):
        raise HTTPException(
            status_code=409,
            detail="Cannot reply to a resolved or closed ticket.",
        )

    reply = SupportTicketReply(
        ticket_id        = ticket_id,
        sender_id        = user_id,
        sender_type      = "user",
        body             = payload.body,
        is_read          = False,
        is_internal_note = False,
        created_by       = user_id,
    )
    reply = await db_create(db, reply)

    # Advance ticket to in_progress if still open
    if ticket.status == "open":
        await db_update(db, SupportTicket, ticket_id, {
            "status":      "in_progress",
            "modified_by": user_id,
        })

    return TicketReplyResponse(
        id               = reply.id,
        ticket_id        = reply.ticket_id,
        sender_id        = reply.sender_id,
        sender_type      = reply.sender_type,
        body             = reply.body,
        is_read          = reply.is_read,
        is_internal_note = reply.is_internal_note,
        created_at       = reply.created_at,
    )


# =============================================================================
# NOTIFICATIONS  (Screen 36)
# =============================================================================

async def help_list_notifications(
    db:              AsyncSession,
    user_id:         uuid.UUID,
    category:        Optional[str]  = None,
    is_read:         Optional[bool] = None,
    page:            int            = 1,
    limit:           int            = 20,
) -> NotificationListResponse:
    """
    Screen 36 — past notifications list.
    Excludes dismissed notifications by default.
    """
    base_filters = [
        Notification.user_id      == user_id,
        Notification.is_dismissed == False,
    ]

    if category:
        base_filters.append(Notification.category == category)
    if is_read is not None:
        base_filters.append(Notification.is_read == is_read)

    # Unread count (always, regardless of filters)
    unread_count = (await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id      == user_id,
            Notification.is_read      == False,
            Notification.is_dismissed == False,
        )
    )).scalar_one()

    # Total matching
    total = (await db.execute(
        select(func.count()).select_from(Notification).where(and_(*base_filters))
    )).scalar_one()

    # Fetch page
    offset = (page - 1) * limit
    rows = (await db.execute(
        select(Notification)
        .where(and_(*base_filters))
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )).scalars().all()

    items = [
        NotificationResponse(
            id                 = n.id,
            notification_type  = n.notification_type,
            category           = n.category,
            priority           = n.priority,
            title              = n.title,
            body               = n.body,
            application_id     = n.application_id,
            case_reference     = n.case_reference,
            cta_primary_label  = n.cta_primary_label,
            cta_primary_url    = n.cta_primary_url,
            is_read            = n.is_read,
            read_at            = n.read_at,
            is_dismissed       = n.is_dismissed,
            sent_via_email     = n.sent_via_email,
            sent_via_push      = n.sent_via_push,
            sent_via_sms       = n.sent_via_sms,
            created_at         = n.created_at,
        )
        for n in rows
    ]

    return NotificationListResponse(
        items        = items,
        total        = total,
        unread_count = unread_count,
    )


async def help_mark_notification_read(
    db:              AsyncSession,
    user_id:         uuid.UUID,
    notification_id: uuid.UUID,
) -> NotificationResponse:
    """
    PATCH /help/notifications/{id}/read
    Marks a single notification as read.
    """
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalars().first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if notif.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    if not notif.is_read:
        await db_update(db, Notification, notification_id, {
            "is_read":    True,
            "read_at":    datetime.now(timezone.utc),
            "modified_by": user_id,
        })
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)

    return NotificationResponse(
        id                 = notif.id,
        notification_type  = notif.notification_type,
        category           = notif.category,
        priority           = notif.priority,
        title              = notif.title,
        body               = notif.body,
        application_id     = notif.application_id,
        case_reference     = notif.case_reference,
        cta_primary_label  = notif.cta_primary_label,
        cta_primary_url    = notif.cta_primary_url,
        is_read            = notif.is_read,
        read_at            = notif.read_at,
        is_dismissed       = notif.is_dismissed,
        sent_via_email     = notif.sent_via_email,
        sent_via_push      = notif.sent_via_push,
        sent_via_sms       = notif.sent_via_sms,
        created_at         = notif.created_at,
    )


async def help_mark_all_notifications_read(
    db:      AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """
    POST /help/notifications/mark-all-read
    Bulk marks all unread notifications as read.
    """
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id  == user_id,
            Notification.is_read  == False,
        )
        .values(is_read=True, read_at=now)
    )
    await db.commit()
    return {"detail": "All notifications marked as read."}


async def help_dismiss_notification(
    db:              AsyncSession,
    user_id:         uuid.UUID,
    notification_id: uuid.UUID,
) -> dict:
    """
    DELETE /help/notifications/{id}
    Soft-dismisses a notification — hides it from the list.
    """
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalars().first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if notif.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    await db_update(db, Notification, notification_id, {
        "is_dismissed": True,
        "dismissed_at": datetime.now(timezone.utc),
        "modified_by":  user_id,
    })
    return {"detail": "Notification dismissed.", "notification_id": str(notification_id)}
