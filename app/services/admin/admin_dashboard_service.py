# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD SERVICE APIs
# ─────────────────────────────────────────────────────────────────────────────

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from typing import List
import uuid


from app.models.visamodels import Role, User, UserLoginHistory, UserRole
from app.schemas.admin.dashboard import (
    DashboardCountsResponse,
    UserLoginCardResponse,
    UserLoginCardListResponse,
)


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD COUNTS
# ─────────────────────────────────────────────────────────────────────────────
async def get_dashboard_counts(
    db: AsyncSession,
) -> DashboardCountsResponse:

    stmt = select(
        func.count(User.id).label("total_users"),
        func.count(User.id)
            .filter(User.is_active.is_(True))
            .label("total_active_users")
    )

    result = await db.execute(stmt)
    row = result.one()

    return DashboardCountsResponse(
        total_users=row.total_users or 0,
        total_active_users=row.total_active_users or 0,
    )
# ─────────────────────────────────────────────────────────────────────────────
# 3. RECENT LOGIN CARDS
# ─────────────────────────────────────────────────────────────────────────────
async def get_recent_login_cards(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> UserLoginCardListResponse:

    stmt = (
        select(
            User.first_name,
            User.last_name,
            User.email,
            Role.name.label("role_name"),
            UserLoginHistory.status,
            UserLoginHistory.is_current_session,
            UserLoginHistory.logged_out_at,
            UserLoginHistory.created_at.label("last_login"),
        )
        .select_from(User)

        # users without login history also included
        .outerjoin(
            UserLoginHistory,
            UserLoginHistory.user_id == User.id
        )

        .join(
            UserRole,
            UserRole.user_id == User.id
        )

        .join(
            Role,
            Role.id == UserRole.role_id
        )

        # DISTINCT ON (u.email)
        .distinct(User.email)

        .order_by(
            User.email,
            UserLoginHistory.created_at.desc().nullslast()
        )

        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        UserLoginCardResponse(
            full_name=f"{row.first_name} {row.last_name}",
            email=row.email,
            role_name=row.role_name,
            status=row.status,
            is_current_session=row.is_current_session,
            logged_out_at=row.logged_out_at,
            last_login=row.last_login,
        )
        for row in rows
    ]

    return UserLoginCardListResponse(items=items)

