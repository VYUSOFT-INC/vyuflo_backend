"""
Organization / tenancy helpers for super_admin vs org_admin scoping.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUserData, Current_User, DBSession
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.visamodels import OrganizationMember, EmployerProfile, Role, UserRole

PLATFORM_ADMIN_ROLES = frozenset({"super_admin", "app_admin"})
ADMIN_CONSOLE_ROLES = frozenset({"super_admin", "app_admin", "org_admin"})
ORG_MEMBER_ROLES = frozenset({"org_admin", "hr", "employee", "attorney"})


def is_platform_admin(roles: list[str] | set[str] | None) -> bool:
    return bool(set(roles or []) & PLATFORM_ADMIN_ROLES)


def is_admin_console_user(roles: list[str] | set[str] | None) -> bool:
    return bool(set(roles or []) & ADMIN_CONSOLE_ROLES)


async def get_user_organization_ids(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    active_only: bool = True,
) -> list[uuid.UUID]:
    stmt = select(OrganizationMember.employer_profile_id).where(
        OrganizationMember.user_id == user_id,
    )
    if active_only:
        stmt = stmt.where(OrganizationMember.is_active == True)  # noqa: E712
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


async def get_primary_organization_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[uuid.UUID]:
    ids = await get_user_organization_ids(db, user_id)
    return ids[0] if ids else None


async def resolve_effective_organization_id(
    db: AsyncSession,
    current_user: CurrentUserData,
) -> Optional[uuid.UUID]:
    """
    Super admin: JWT active_organization_id, else Redis session context.
    Org admin / members: forced to their membership org(s); prefer JWT if valid.
    """
    roles = set(current_user.roles or [])
    active = getattr(current_user, "active_organization_id", None)

    if is_platform_admin(roles):
        if active:
            return active
        # Fallback when access token predates switch but Redis was updated
        try:
            from app.core.redis import redis_get
            stored = await redis_get(f"active_org:{current_user.user_id}")
            if stored:
                return uuid.UUID(stored)
        except Exception:
            pass
        return None

    org_ids = await get_user_organization_ids(db, current_user.user_id)
    if not org_ids:
        return None
    if active and active in org_ids:
        return active
    return org_ids[0]


async def require_list_organization_id(
    db: AsyncSession,
    current_user: CurrentUserData,
) -> Optional[uuid.UUID]:
    """
    Organization filter for list/stats APIs.
    - Platform admin with no org context → None (global, still hide platform users).
    - Platform admin entered into an org → that org id.
    - Org admin / non-platform → must have a membership org (fail closed).
    """
    org_id = await resolve_effective_organization_id(db, current_user)
    if is_platform_admin(current_user.roles):
        return org_id
    if org_id is None:
        raise ForbiddenException(
            "No organization membership. Contact a platform admin."
        )
    return org_id


async def assert_platform_console(
    db: AsyncSession,
    current_user: CurrentUserData,
) -> None:
    """Block platform-wide admin tools while an org context is active."""
    org_id = await resolve_effective_organization_id(db, current_user)
    if org_id is not None:
        raise ForbiddenException(
            "This is a platform-only tool. Exit the organization first."
        )
    if not is_platform_admin(current_user.roles):
        raise ForbiddenException("Platform admin access required.")


async def assert_not_switched_away_from_org(
    db: AsyncSession,
    current_user: CurrentUserData,
    organization_id: uuid.UUID,
) -> None:
    """When viewing an org context, block access to other orgs."""
    active = await resolve_effective_organization_id(db, current_user)
    if active and active != organization_id:
        raise ForbiddenException(
            "You are viewing another organization. Exit that organization first."
        )


async def assert_user_in_active_org(
    db: AsyncSession,
    current_user: CurrentUserData,
    target_user_id: uuid.UUID,
) -> None:
    """When org-scoped, target user must be an active member of that org."""
    org_id = await resolve_effective_organization_id(db, current_user)
    if org_id is None and is_platform_admin(current_user.roles):
        return
    if org_id is None:
        raise ForbiddenException("No organization context.")
    member = (
        await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.employer_profile_id == org_id,
                OrganizationMember.user_id == target_user_id,
                OrganizationMember.is_active == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if not member:
        raise ForbiddenException("User is not in the active organization.")



async def require_org_access(
    db: AsyncSession,
    current_user: CurrentUserData,
    organization_id: uuid.UUID,
) -> EmployerProfile:
    org = (
        await db.execute(
            select(EmployerProfile).where(EmployerProfile.id == organization_id)
        )
    ).scalar_one_or_none()
    if not org:
        raise NotFoundException("Organization not found.")

    if is_platform_admin(current_user.roles):
        return org

    member = (
        await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.employer_profile_id == organization_id,
                OrganizationMember.user_id == current_user.user_id,
                OrganizationMember.is_active == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if not member:
        raise ForbiddenException("You do not have access to this organization.")
    return org


async def get_org_member_user_ids(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    include_platform: bool = False,
) -> list[uuid.UUID]:
    stmt = select(OrganizationMember.user_id).where(
        OrganizationMember.employer_profile_id == organization_id,
        OrganizationMember.is_active == True,  # noqa: E712
    )
    ids = list((await db.execute(stmt)).scalars().all())
    if include_platform:
        return ids
    return ids


async def upsert_organization_member(
    db: AsyncSession,
    *,
    employer_profile_id: uuid.UUID,
    user_id: uuid.UUID,
    org_role: str,
    changed_by: Optional[uuid.UUID] = None,
) -> OrganizationMember:
    if org_role not in ORG_MEMBER_ROLES:
        raise ForbiddenException(f"Invalid org_role: {org_role}")

    existing = (
        await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.employer_profile_id == employer_profile_id,
                OrganizationMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.org_role = org_role
        existing.is_active = True
        existing.modified_by = changed_by
        await db.flush()
        return existing

    row = OrganizationMember(
        id=uuid.uuid4(),
        employer_profile_id=employer_profile_id,
        user_id=user_id,
        org_role=org_role,
        is_active=True,
        created_by=changed_by,
        modified_by=changed_by,
    )
    db.add(row)
    await db.flush()
    return row


async def assign_global_role(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    role_name: str,
    changed_by: Optional[uuid.UUID] = None,
) -> None:
    from sqlalchemy import delete

    role = (
        await db.execute(select(Role).where(Role.name == role_name, Role.is_active == True))
    ).scalar_one_or_none()
    if not role:
        raise NotFoundException(f"Role '{role_name}' not found.")

    await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    db.add(UserRole(
        id=uuid.uuid4(),
        user_id=user_id,
        role_id=role.id,
        assigned_by=changed_by,
        created_by=changed_by,
        modified_by=changed_by,
    ))
    await db.flush()


async def require_platform_console_dep(
    current_user: Current_User,
    db: DBSession,
) -> None:
    """FastAPI dependency: platform-only admin tools (not while in an org)."""
    await assert_platform_console(db, current_user)
