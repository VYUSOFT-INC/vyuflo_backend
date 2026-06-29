"""
app/routers/admin_support_router.py

API routes for ADMIN-12 Help & Support (Admin).

Endpoints:
    GET  /admin/support/articles          → FAQ list + Popular Articles + Search
    GET  /admin/support/articles/{id}     → Single article / FAQ detail
    GET  /admin/support/system-status     → System Status card
    POST /admin/support/tickets           → Submit a Ticket ("Create Ticket" button)

⚠️  Adjust these two imports to match your project:
    get_db           → yields AsyncSession
    get_current_user → returns authenticated User (must have .user_id)
    (Copy the exact path from your other routers, e.g. roles.py)
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

# ⚠️ Adjust import paths to match your project
from app.core.core_permissions import get_current_user, get_db
from app.models.visamodels import User

from app.services.admin import admin_support_service
from app.schemas.admin.admin_support import (
    ArticleListResponse,
    ArticleResponse,
    SystemStatusResponse,
    TicketCreate,
    TicketResponse,
)

admin_support_router = APIRouter(tags=["Admin — Help & Support"])


# =============================================================================
# ARTICLES  —  FAQ list | Popular Articles | Search
# =============================================================================

@admin_support_router.get(
    "/admin/support/articles",
    response_model=ArticleListResponse,
    summary="List articles — FAQ list, Popular Articles sidebar, and Search",
)
async def list_articles(
    # Pagination
    page:  int = Query(default=1,  ge=1,          description="Page number"),
    limit: int = Query(default=10, ge=1,  le=100,  description="Items per page"),

    # Category tab filter — matches the tab bar on the screen
    # Values: "all" | "platform_config" | "user_management" | "billing" | "integrations" | "security"
    category: Optional[str] = Query(default=None, description="Category tab filter"),

    # Free-text search (Search bar at the top of the screen)
    search: Optional[str] = Query(default=None, description="Search articles and FAQs"),

    # article_type filter — pass "faq" for the FAQ accordion section
    article_type: Optional[str] = Query(
        default=None,
        description="Filter by type: faq | guide | video_tutorial | policy"
    ),

    # featured=true → Popular Articles sidebar (top 3 featured articles)
    featured: Optional[bool] = Query(default=None, description="True = Popular Articles only"),

    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Single endpoint powers three UI components:

    1. FAQ Accordion section:
       GET /admin/support/articles?article_type=faq

    2. Popular Articles sidebar (top 3):
       GET /admin/support/articles?featured=true&limit=3

    3. Search bar:
       GET /admin/support/articles?search=reset+password

    4. Category tab filter:
       GET /admin/support/articles?category=billing
    """
    return await admin_support_service.service_list_articles(
        db           = db,
        page         = page,
        limit        = limit,
        category     = category,
        search       = search,
        featured     = featured,
        article_type = article_type,
    )


@admin_support_router.get(
    "/admin/support/articles/{article_id}",
    response_model=ArticleResponse,
    summary="Get single article / FAQ detail",
)
async def get_article(
    article_id:   uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Called when admin expands a FAQ accordion item or clicks a Popular Article link.
    Also increments view_count on the article.
    """
    return await admin_support_service.service_get_article(db, article_id)


# =============================================================================
# SYSTEM STATUS  —  System Status card (right sidebar)
# =============================================================================

@admin_support_router.get(
    "/admin/support/system-status",
    response_model=SystemStatusResponse,
    summary="Get System Status card — reads from system_settings table",
)
async def get_system_status(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Powers the System Status card on the right side of the screen.

    Data is stored in the existing system_settings table using these keys:
      system.core_platform_status       → "operational" | "degraded" | "down"
      system.core_platform_uptime       → "100% Uptime"
      system.integrations_api_status    → "operational"
      system.integrations_api_uptime    → "99.9% Uptime"
      system.uscis_portal_status        → "operational"
      system.status_page_url            → "https://status.visaflow.com"

    Seed these rows once in seeds.py — no new table needed.
    """
    return await admin_support_service.service_get_system_status(db)


# =============================================================================
# TICKETS  —  Submit a Ticket ("Create Ticket" button)
# =============================================================================

@admin_support_router.post(
    "/admin/support/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a support ticket — 'Create Ticket' button",
)
async def create_ticket(
    payload:      TicketCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Called when admin clicks "Create Ticket" on the Help & Support screen.

    Request body example:
    {
        "subject":  "Cannot configure USCIS integration",
        "body":     "Getting 403 error when trying to connect USCIS portal.",
        "category": "technical",
        "priority": "high"
    }
    """
    return await admin_support_service.service_create_ticket(
        db          = db,
        payload     = payload,
        created_by  = current_user.user_id,
    )
