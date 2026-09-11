# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD SERVICE APIs
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import Optional
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import OrganizationMember, Role, User, UserLoginHistory, UserRole
from app.schemas.admin.dashboard import (
    DashboardCountsResponse,
    UserLoginCardResponse,
    UserLoginCardListResponse,
)


def _org_member_user_ids(organization_id: uuid.UUID):
    return (
        select(OrganizationMember.user_id)
        .where(
            OrganizationMember.employer_profile_id == organization_id,
            OrganizationMember.is_active == True,  # noqa: E712
        )
    )


async def get_dashboard_counts(
    db: AsyncSession,
    *,
    organization_id: Optional[uuid.UUID] = None,
) -> DashboardCountsResponse:
    stmt = select(
        func.count(User.id).label("total_users"),
        func.count(User.id)
            .filter(User.is_active.is_(True))
            .label("total_active_users"),
    ).where(User.is_platform_user == False)  # noqa: E712

    if organization_id is not None:
        stmt = stmt.where(User.id.in_(_org_member_user_ids(organization_id)))

    result = await db.execute(stmt)
    row = result.one()

    return DashboardCountsResponse(
        total_users=row.total_users or 0,
        total_active_users=row.total_active_users or 0,
    )


async def get_recent_login_cards(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    *,
    organization_id: Optional[uuid.UUID] = None,
) -> UserLoginCardListResponse:

    stmt = (
        select(
            User.first_name,
            User.last_name,
            User.email,
            Role.name.label("role_name"),
            UserLoginHistory.status,
            UserLoginHistory.created_at.label("last_login"),
        )
        .select_from(User)
        .outerjoin(
            UserLoginHistory,
            UserLoginHistory.user_id == User.id,
        )
        .join(
            UserRole,
            UserRole.user_id == User.id,
        )
        .join(
            Role,
            Role.id == UserRole.role_id,
        )
        .where(User.is_platform_user == False)  # noqa: E712
        .distinct(User.email)
        .order_by(
            User.email,
            UserLoginHistory.created_at.desc().nullslast(),
        )
        .limit(limit)
        .offset(offset)
    )

    if organization_id is not None:
        stmt = stmt.where(User.id.in_(_org_member_user_ids(organization_id)))

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        UserLoginCardResponse(
            full_name=f"{row.first_name} {row.last_name}",
            email=row.email,
            role_name=row.role_name,
            status=row.status,
            last_login=row.last_login,
        )
        for row in rows
    ]

    return UserLoginCardListResponse(items=items)
