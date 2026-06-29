"""
app/services/admin_support_service.py

Business logic for ADMIN-12 Help & Support (Admin).

All DB operations are async SQLAlchemy.
Raises exceptions from app.core.exceptions — routers never catch these,
the global handler in exceptions.py handles them.

Tables used (NO new tables added):
  - support_articles   → FAQ list, Popular Articles, Search
  - system_settings    → System Status card
  - support_tickets    → Submit a Ticket
"""

from __future__ import annotations

import uuid
import math
from typing import Optional

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException

# ⚠️ Adjust import path to match your project
from app.models.visamodels import SupportArticle, SupportTicket, SystemSetting

from app.schemas.admin.admin_support import (
    ArticleListResponse,
    ArticleResponse,
    ServiceStatusItem,
    SystemStatusResponse,
    TicketCreate,
    TicketResponse,
)


# =============================================================================
# SYSTEM STATUS  (reads from system_settings table — no new table)
# =============================================================================

# These keys must exist as rows in your system_settings table.
# Seed them once (see seeds.py) — never hardcode values in code.
_STATUS_KEYS = [
    "system.core_platform_status",
    "system.core_platform_uptime",
    "system.integrations_api_status",
    "system.integrations_api_uptime",
    "system.uscis_portal_status",
    "system.status_page_url",
]

_SERVICE_MAP = {
    # setting_key_prefix         display name
    "system.core_platform":    "Core Platform",
    "system.integrations_api": "Integrations API",
    "system.uscis_portal":     "USCIS Portal Sync",
}


async def service_get_system_status(db: AsyncSession) -> SystemStatusResponse:
    """
    Reads service health rows from system_settings.
    Returns the System Status card data for ADMIN-12.
    """
    result = await db.execute(
        select(SystemSetting).where(
            SystemSetting.key.like("system.%_status").or_(
                SystemSetting.key.like("system.%_uptime"),
                SystemSetting.key == "system.status_page_url",
            )
        )
    )
    rows: dict[str, str] = {r.key: r.value for r in result.scalars().all()}

    services: list[ServiceStatusItem] = []
    for prefix, display_name in _SERVICE_MAP.items():
        status_val   = rows.get(f"{prefix}_status",  "operational")
        uptime_label = rows.get(f"{prefix}_uptime",  None)
        services.append(ServiceStatusItem(
            service_name  = display_name,
            status        = status_val,
            uptime_label  = uptime_label,
            status_badge  = _status_to_badge(status_val),
        ))

    # Overall badge — worst status wins
    statuses = [s.status for s in services]
    if "down" in statuses:
        overall = "Outage"
    elif "degraded" in statuses:
        overall = "Partial Outage"
    else:
        overall = "All Systems Operational"

    return SystemStatusResponse(
        overall_status        = overall,
        services              = services,
        view_status_page_url  = rows.get("system.status_page_url"),
    )


def _status_to_badge(status: str) -> str:
    return {
        "operational": "All Systems Operational",
        "degraded":    "Partial Outage",
        "down":        "Outage",
    }.get(status, "All Systems Operational")


# =============================================================================
# ARTICLES  (FAQ list + Popular Articles + Search)
# =============================================================================

# Admin-facing category tab values on the screen map to these DB values.
# The screen shows: All Categories | Platform Config | User Management |
#                   Billing | Integrations | Security
# Your existing category enum uses slightly different names — map here.
_ADMIN_CATEGORY_MAP: dict[str, str | None] = {
    "all":              None,              # no filter
    "platform_config":  "visa_types",      # closest match — or extend enum
    "user_management":  "account_profile",
    "billing":          "billing_payments",
    "integrations":     "technical",
    "security":         "technical",
}


async def service_list_articles(
    db:       AsyncSession,
    page:     int = 1,
    limit:    int = 10,
    category: Optional[str] = None,   # admin tab value: "all", "billing", etc.
    search:   Optional[str] = None,   # free-text search
    featured: Optional[bool] = None,  # True → Popular Articles sidebar
    article_type: Optional[str] = None,  # "faq" | "guide" | ...
) -> ArticleListResponse:
    """
    Single service function used by:
      - FAQ accordion list          (article_type="faq")
      - Popular Articles sidebar    (featured=True, limit=3)
      - Search results              (search="...")
      - Category tab filter         (category="billing")
    """
    filters = [
        SupportArticle.is_published == True,
        SupportArticle.is_active == True,
    ]

    # Category tab filter
    if category and category != "all":
        db_category = _ADMIN_CATEGORY_MAP.get(category)
        if db_category:
            filters.append(SupportArticle.category == db_category)

    # Article type filter (FAQ vs guide etc.)
    if article_type:
        filters.append(SupportArticle.article_type == article_type)

    # Featured filter for Popular Articles sidebar
    if featured is not None:
        filters.append(SupportArticle.is_featured == featured)

    # Free-text search across title, summary, search_keywords
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                SupportArticle.title.ilike(term),
                SupportArticle.summary.ilike(term),
                SupportArticle.search_keywords.ilike(term),
            )
        )

    # Count total
    count_q = select(func.count()).select_from(SupportArticle).where(and_(*filters))
    total   = (await db.execute(count_q)).scalar_one()

    # Fetch page
    offset = (page - 1) * limit
    rows_q = (
        select(SupportArticle)
        .where(and_(*filters))
        .order_by(SupportArticle.sort_order.asc(), SupportArticle.view_count.desc())
        .offset(offset)
        .limit(limit)
    )
    articles = (await db.execute(rows_q)).scalars().all()

    return ArticleListResponse(
        items       = [ArticleResponse.model_validate(a) for a in articles],
        total       = total,
        page        = page,
        limit       = limit,
        total_pages = math.ceil(total / limit) if total else 1,
    )


async def service_get_article(
    db: AsyncSession,
    article_id: uuid.UUID,
) -> ArticleResponse:
    """
    Returns single article detail — used when admin clicks an FAQ item
    to expand full body, or clicks a Popular Article link.
    """
    result = await db.execute(
        select(SupportArticle).where(
            SupportArticle.id         == article_id,
            SupportArticle.is_active  == True,
            SupportArticle.is_published == True,
        )
    )
    article = result.scalar_one_or_none()
    if not article:
        raise NotFoundException("Article not found.")

    # Increment view count (fire-and-forget style — no await needed for analytics)
    article.view_count = (article.view_count or 0) + 1
    await db.flush()

    return ArticleResponse.model_validate(article)


# =============================================================================
# TICKET  (Submit a Ticket — "Create Ticket" button)
# =============================================================================

async def service_create_ticket(
    db:          AsyncSession,
    payload:     TicketCreate,
    created_by:  uuid.UUID,
) -> TicketResponse:
    """
    Admin submits a support ticket (e.g. for a platform issue).
    Ticket number auto-generated as TICK-YYYYMMDD-XXXX.
    """
    # Validate category
    valid_categories = {
        "account_profile", "active_cases", "documents",
        "billing_payments", "visa_types", "technical", "other",
    }
    if payload.category not in valid_categories:
        raise BadRequestException(
            f"Invalid category '{payload.category}'. "
            f"Allowed: {', '.join(sorted(valid_categories))}"
        )

    # Validate priority
    valid_priorities = {"urgent", "high", "medium", "low"}
    if payload.priority not in valid_priorities:
        raise BadRequestException(
            f"Invalid priority '{payload.priority}'. "
            f"Allowed: {', '.join(sorted(valid_priorities))}"
        )

    # Generate ticket number: TICK-20250604-0001 style
    from datetime import datetime, timezone
    today_str    = datetime.now(timezone.utc).strftime("%Y%m%d")
    count_today  = (
        await db.execute(
            select(func.count()).select_from(SupportTicket).where(
                func.date(SupportTicket.created_at) == func.current_date()
            )
        )
    ).scalar_one()
    ticket_number = f"TICK-{today_str}-{str(count_today + 1).zfill(4)}"

    ticket = SupportTicket(
        id            = uuid.uuid4(),
        ticket_number = ticket_number,
        user_id       = created_by,
        subject       = payload.subject.strip(),
        body          = payload.body.strip(),
        category      = payload.category,
        priority      = payload.priority,
        status        = "open",
        channel       = "web_form",
        created_by    = created_by,
        modified_by   = created_by,
    )
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket)

    return TicketResponse.model_validate(ticket)
