# =============================================================================
# app/routers/help.py
#
# Lawyer-facing Help & Support endpoints (Screens 28–36).
# Your existing admin_support router is NOT touched.
#
# Register in main.py:
#   from app.routers.help import help_router
#   app.include_router(help_router, prefix="/api/v1", tags=["Help & Support"])
#
# Screens covered:
#   28, 29  — Static pages, no API needed
#   30      — GET /help/articles?search=
#   31      — GET /help/articles  (browse + popular)
#   31      — GET /help/articles/{id}
#   32      — POST /help/tickets
#   33      — GET /help/tickets
#   34      — GET /help/tickets/{id}
#   34      — POST /help/tickets/{id}/replies
#   35      — GET /help/tickets/{id}  (same endpoint, used for confirmation)
#   36      — GET /help/notifications
#   36      — PATCH /help/notifications/{id}/read
#   36      — POST /help/notifications/mark-all-read
#   36      — DELETE /help/notifications/{id}
# =============================================================================

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user

# Reuse existing admin article schemas for article responses
from app.schemas.admin.admin_support import ArticleListResponse, ArticleResponse

# New help-specific schemas
from app.schemas.attorney.help import (
    NotificationListResponse,
    NotificationResponse,
    TicketCreate,
    TicketDetailResponse,
    TicketListResponse,
    TicketReplyCreate,
    TicketReplyResponse,
)

# Service functions
from app.services.attorney.help_service import (
    help_create_ticket,
    help_dismiss_notification,
    help_get_article,
    help_get_ticket_detail,
    help_list_articles,
    help_list_my_tickets,
    help_list_notifications,
    help_mark_all_notifications_read,
    help_mark_notification_read,
    help_reply_to_ticket,
)

help_router = APIRouter()


# =============================================================================
# ARTICLES  —  /help/articles
# Screens 30 (search) + 31 (browse/popular)
# =============================================================================

@help_router.get(
    "/help/articles",
    response_model=ArticleListResponse,
    status_code=status.HTTP_200_OK,
    summary="List / search help articles and FAQs",
    description="""
Powers three UI components:

**Screen 30 — Search Results:**
`GET /help/articles?search=passport`

**Screen 31 — Browse by category:**
`GET /help/articles?category=billing`

**Screen 31 — Popular Articles sidebar:**
`GET /help/articles?featured=true&limit=3`

**Screen 31 — FAQ section:**
`GET /help/articles?article_type=faq`
    """,
)
async def api_help_list_articles(
    page:         int            = Query(default=1,    ge=1),
    limit:        int            = Query(default=10,   ge=1, le=100),
    search:       Optional[str]  = Query(default=None, description="Free-text search — Screen 30"),
    category:     Optional[str]  = Query(default=None, description="all | platform_config | user_management | billing | integrations | security"),
    article_type: Optional[str]  = Query(default=None, description="faq | guide | video_tutorial | policy"),
    featured:     Optional[bool] = Query(default=None, description="True = Popular Articles only"),
    db:           AsyncSession   = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> ArticleListResponse:
    return await help_list_articles(
        db           = db,
        page         = page,
        limit        = limit,
        category     = category,
        search       = search,
        featured     = featured,
        article_type = article_type,
    )


@help_router.get(
    "/help/articles/{article_id}",
    response_model=ArticleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single article detail — Screen 31 expanded view",
    description="Also increments view_count on the article.",
)
async def api_help_get_article(
    article_id:  uuid.UUID,
    db:          AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> ArticleResponse:
    return await help_get_article(db, article_id)


# =============================================================================
# TICKETS  —  /help/tickets
# Screen 32 (submit), 33 (my list), 34 (detail + replies), 35 (confirmation)
# =============================================================================

@help_router.post(
    "/help/tickets",
    response_model=TicketDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a support ticket — Screen 32",
    description="""
Lawyer submits a help request.
Optionally linked to an application via `application_id`.
Returns full ticket detail — used immediately by Screen 35 (Ticket Submitted confirmation).
    """,
)
async def api_help_create_ticket(
    payload:     TicketCreate,
    db:          AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> TicketDetailResponse:
    return await help_create_ticket(db, current_user.user_id, payload)


@help_router.get(
    "/help/tickets",
    response_model=TicketListResponse,
    status_code=status.HTTP_200_OK,
    summary="List my support tickets — Screen 33",
    description="""
Returns only tickets submitted by the current lawyer.
Use `status` query param to filter by tab:
  - `open`, `in_progress`, `resolved`, `closed`, `waiting_user`
Response includes `open`, `in_progress`, `resolved` counts for tab badges.
    """,
)
async def api_help_list_my_tickets(
    status_filter:   Optional[str] = Query(default=None, alias="status",   description="Filter by ticket status"),
    category_filter: Optional[str] = Query(default=None, alias="category", description="Filter by category"),
    page:            int           = Query(default=1,  ge=1),
    limit:           int           = Query(default=20, ge=1, le=100),
    db:              AsyncSession  = Depends(get_db),
    current_user                   = Depends(get_current_user),
) -> TicketListResponse:
    return await help_list_my_tickets(
        db             = db,
        user_id        = current_user.user_id,
        status_filter  = status_filter,
        category_filter= category_filter,
        page           = page,
        limit          = limit,
    )


@help_router.get(
    "/help/tickets/{ticket_id}",
    response_model=TicketDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ticket detail with reply thread — Screen 34 + Screen 35 confirmation",
    description="""
Screen 34 — full ticket detail + conversation thread (internal notes hidden from lawyer).
Screen 35 — also uses this endpoint to show just-submitted ticket confirmation.
    """,
)
async def api_help_get_ticket_detail(
    ticket_id:   uuid.UUID,
    db:          AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> TicketDetailResponse:
    return await help_get_ticket_detail(db, current_user.user_id, ticket_id)


@help_router.post(
    "/help/tickets/{ticket_id}/replies",
    response_model=TicketReplyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reply to a support ticket — Screen 34",
    description="""
Lawyer adds a follow-up reply to their ticket.
Automatically advances ticket status from `open` → `in_progress`.
Returns 409 if ticket is already resolved or closed.
    """,
)
async def api_help_reply_to_ticket(
    ticket_id:   uuid.UUID,
    payload:     TicketReplyCreate,
    db:          AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> TicketReplyResponse:
    return await help_reply_to_ticket(
        db        = db,
        user_id   = current_user.user_id,
        ticket_id = ticket_id,
        payload   = payload,
    )


# =============================================================================
# NOTIFICATIONS  —  /help/notifications
# Screen 36 — past notifications list
# =============================================================================

@help_router.get(
    "/help/notifications",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List past notifications — Screen 36",
    description="""
Returns the lawyer's notification history (excludes dismissed).
Filter by `category`: case_update | deadline | news | security | billing
Filter by `is_read`: true | false
Response includes `unread_count` for the bell badge.
    """,
)
async def api_help_list_notifications(
    category: Optional[str]  = Query(default=None, description="case_update | deadline | news | security | billing"),
    is_read:  Optional[bool] = Query(default=None, description="true = read only, false = unread only"),
    page:     int            = Query(default=1,  ge=1),
    limit:    int            = Query(default=20, ge=1, le=100),
    db:       AsyncSession   = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> NotificationListResponse:
    return await help_list_notifications(
        db       = db,
        user_id  = current_user.user_id,
        category = category,
        is_read  = is_read,
        page     = page,
        limit    = limit,
    )


@help_router.patch(
    "/help/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a single notification as read — Screen 36",
)
async def api_help_mark_notification_read(
    notification_id: uuid.UUID,
    db:              AsyncSession = Depends(get_db),
    current_user                  = Depends(get_current_user),
) -> NotificationResponse:
    return await help_mark_notification_read(
        db              = db,
        user_id         = current_user.user_id,
        notification_id = notification_id,
    )


@help_router.post(
    "/help/notifications/mark-all-read",
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read — Screen 36 'Mark all read' button",
)
async def api_help_mark_all_read(
    db:          AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> dict:
    return await help_mark_all_notifications_read(db, current_user.user_id)


@help_router.delete(
    "/help/notifications/{notification_id}",
    status_code=status.HTTP_200_OK,
    summary="Dismiss (hide) a notification — Screen 36",
)
async def api_help_dismiss_notification(
    notification_id: uuid.UUID,
    db:              AsyncSession = Depends(get_db),
    current_user                  = Depends(get_current_user),
) -> dict:
    return await help_dismiss_notification(
        db              = db,
        user_id         = current_user.user_id,
        notification_id = notification_id,
    )
