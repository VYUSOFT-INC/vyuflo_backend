"""
Admin organization tenancy service.
Organizations = employer_profiles; membership via organization_members.
"""
from __future__ import annotations

import math
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.org_scope import assign_global_role, upsert_organization_member
from app.core.security import hash_password
from app.models.visamodels import (
    EmployerProfile,
    OrganizationMember,
    User,
    UserEmail,
    UserProfile,
)


def _add_verified_login_email(db: AsyncSession, user_id: uuid.UUID, email: str) -> None:
    db.add(UserEmail(
        user_id=user_id,
        email=email.lower().strip(),
        is_verified=True,
        is_primary=True,
        source="signup",
    ))


def _split_name(name: str) -> tuple[str, str]:
    parts = (name or "").strip().split(None, 1)
    if not parts:
        return "Org", "Admin"
    if len(parts) == 1:
        return parts[0], "Admin"
    return parts[0], parts[1]


async def service_list_organizations(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
) -> dict:
    stmt = select(EmployerProfile)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(EmployerProfile.company_name.ilike(pattern))

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    offset = (page - 1) * limit
    profiles = (
        await db.execute(
            stmt.order_by(EmployerProfile.created_at.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()

    items = []
    for ep in profiles:
        member_count = (
            await db.execute(
                select(func.count()).where(
                    OrganizationMember.employer_profile_id == ep.id,
                    OrganizationMember.is_active == True,  # noqa: E712
                )
            )
        ).scalar_one()
        admin_count = (
            await db.execute(
                select(func.count()).where(
                    OrganizationMember.employer_profile_id == ep.id,
                    OrganizationMember.org_role == "org_admin",
                    OrganizationMember.is_active == True,  # noqa: E712
                )
            )
        ).scalar_one()
        owner = (
            await db.execute(select(User).where(User.id == ep.user_id))
        ).scalar_one_or_none()
        items.append({
            "id": str(ep.id),
            "company_name": ep.company_name,
            "industry": ep.industry,
            "is_active": ep.is_active,
            "is_verified": ep.is_verified,
            "member_count": member_count,
            "admin_count": admin_count,
            "owner_email": owner.email if owner else None,
            "created_at": ep.created_at,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if limit else 1,
    }


async def service_get_organization(db: AsyncSession, org_id: uuid.UUID) -> dict:
    ep = (
        await db.execute(select(EmployerProfile).where(EmployerProfile.id == org_id))
    ).scalar_one_or_none()
    if not ep:
        raise NotFoundException("Organization not found.")

    members_rows = (
        await db.execute(
            select(OrganizationMember, User)
            .join(User, User.id == OrganizationMember.user_id)
            .where(OrganizationMember.employer_profile_id == org_id)
            .order_by(OrganizationMember.org_role.asc(), User.email.asc())
        )
    ).all()

    members = []
    for mem, user in members_rows:
        # Never expose platform super admins in org member lists
        if getattr(user, "is_platform_user", False):
            continue
        members.append({
            "user_id": str(user.id),
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "org_role": mem.org_role,
            "is_active": mem.is_active,
        })

    owner = (
        await db.execute(select(User).where(User.id == ep.user_id))
    ).scalar_one_or_none()

    return {
        "id": str(ep.id),
        "company_name": ep.company_name,
        "industry": ep.industry,
        "website": ep.website,
        "domain": ep.domain,
        "is_active": ep.is_active,
        "is_verified": ep.is_verified,
        "member_count": len(members),
        "admin_count": sum(1 for m in members if m["org_role"] == "org_admin"),
        "owner_email": owner.email if owner else None,
        "created_at": ep.created_at,
        "members": members,
    }


async def service_create_organization(
    db: AsyncSession,
    *,
    company_name: str,
    industry: Optional[str],
    website: Optional[str],
    domain: Optional[str],
    admin_email: Optional[str],
    admin_name: Optional[str],
    admin_password: Optional[str],
    created_by: uuid.UUID,
) -> dict:
    owner_user: Optional[User] = None

    if admin_email:
        existing = (
            await db.execute(select(User).where(User.email == admin_email))
        ).scalar_one_or_none()
        if existing and getattr(existing, "is_platform_user", False):
            raise BadRequestException("Cannot assign a platform super admin as org admin.")
        if existing:
            owner_user = existing
        else:
            first, last = _split_name(admin_name or admin_email.split("@")[0])
            pwd = admin_password or "Password!"
            normalized = admin_email.lower().strip()
            owner_user = User(
                id=uuid.uuid4(),
                first_name=first,
                last_name=last,
                email=normalized,
                password_hash=hash_password(pwd),
                auth_provider="email",
                is_active=True,
                is_verified=True,
                terms_accepted=True,
                is_platform_user=False,
                created_by=created_by,
            )
            db.add(owner_user)
            await db.flush()
            _add_verified_login_email(db, owner_user.id, normalized)
            db.add(UserProfile(
                user_id=owner_user.id,
                full_legal_name=f"{first} {last}",
                onboarding_step=4,
                onboarding_completed=True,
            ))
            await assign_global_role(
                db, user_id=owner_user.id, role_name="org_admin", changed_by=created_by,
            )
    else:
        # Placeholder owner = creator (super admin) — still need a user_id FK.
        # Prefer creating a dedicated inactive shell is messy; require admin_email.
        raise BadRequestException("admin_email is required when creating an organization.")

    ep = EmployerProfile(
        id=uuid.uuid4(),
        user_id=owner_user.id,
        company_name=company_name,
        industry=industry,
        website=website,
        domain=domain,
        is_active=True,
        is_verified=False,
        created_by=created_by,
        modified_by=created_by,
    )
    db.add(ep)
    await db.flush()

    await upsert_organization_member(
        db,
        employer_profile_id=ep.id,
        user_id=owner_user.id,
        org_role="org_admin",
        changed_by=created_by,
    )
    await db.commit()
    return await service_get_organization(db, ep.id)


async def service_update_organization(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    company_name: Optional[str] = None,
    industry: Optional[str] = None,
    website: Optional[str] = None,
    domain: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    modified_by: uuid.UUID,
) -> dict:
    ep = (
        await db.execute(select(EmployerProfile).where(EmployerProfile.id == org_id))
    ).scalar_one_or_none()
    if not ep:
        raise NotFoundException("Organization not found.")

    if company_name is not None:
        ep.company_name = company_name
    if industry is not None:
        ep.industry = industry
    if website is not None:
        ep.website = website
    if domain is not None:
        ep.domain = domain
    if is_active is not None:
        ep.is_active = is_active
    if is_verified is not None:
        ep.is_verified = is_verified
    ep.modified_by = modified_by
    await db.commit()
    return await service_get_organization(db, org_id)


async def service_add_org_admin(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    email: str,
    name: str,
    password: Optional[str],
    created_by: uuid.UUID,
) -> dict:
    ep = (
        await db.execute(select(EmployerProfile).where(EmployerProfile.id == org_id))
    ).scalar_one_or_none()
    if not ep:
        raise NotFoundException("Organization not found.")

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user and getattr(user, "is_platform_user", False):
        raise ForbiddenException("Cannot assign a platform super admin as org admin.")

    if user is None:
        first, last = _split_name(name)
        normalized = email.lower().strip()
        user = User(
            id=uuid.uuid4(),
            first_name=first,
            last_name=last,
            email=normalized,
            password_hash=hash_password(password or "Password!"),
            auth_provider="email",
            is_active=True,
            is_verified=True,
            terms_accepted=True,
            is_platform_user=False,
            created_by=created_by,
        )
        db.add(user)
        await db.flush()
        _add_verified_login_email(db, user.id, normalized)
        db.add(UserProfile(
            user_id=user.id,
            full_legal_name=f"{first} {last}",
            onboarding_step=4,
            onboarding_completed=True,
        ))
    else:
        if password:
            user.password_hash = hash_password(password)

    await assign_global_role(
        db, user_id=user.id, role_name="org_admin", changed_by=created_by,
    )
    await upsert_organization_member(
        db,
        employer_profile_id=org_id,
        user_id=user.id,
        org_role="org_admin",
        changed_by=created_by,
    )
    await db.commit()
    return await service_get_organization(db, org_id)


async def service_remove_org_admin(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    modified_by: uuid.UUID,
) -> dict:
    mem = (
        await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.employer_profile_id == org_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.org_role == "org_admin",
            )
        )
    ).scalar_one_or_none()
    if not mem:
        raise NotFoundException("Org admin membership not found.")

    mem.is_active = False
    mem.modified_by = modified_by
    await db.commit()
    return await service_get_organization(db, org_id)


async def service_create_super_admin(
    db: AsyncSession,
    *,
    email: str,
    name: str,
    password: str,
    created_by: uuid.UUID,
) -> dict:
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise BadRequestException("A user with this email already exists.")

    first, last = _split_name(name)
    normalized = email.lower().strip()
    user = User(
        id=uuid.uuid4(),
        first_name=first,
        last_name=last,
        email=normalized,
        password_hash=hash_password(password),
        auth_provider="email",
        is_active=True,
        is_verified=True,
        terms_accepted=True,
        is_platform_user=True,
        created_by=created_by,
    )
    db.add(user)
    await db.flush()
    _add_verified_login_email(db, user.id, normalized)
    db.add(UserProfile(
        user_id=user.id,
        full_legal_name=f"{first} {last}",
        onboarding_step=4,
        onboarding_completed=True,
    ))
    await assign_global_role(
        db, user_id=user.id, role_name="super_admin", changed_by=created_by,
    )
    await db.commit()
    return {
        "id": str(user.id),
        "email": user.email,
        "name": f"{user.first_name} {user.last_name}".strip(),
        "role": "super_admin",
        "is_platform_user": True,
    }
