"""Service layer for per-user permission overrides."""
from __future__ import annotations

import json
import uuid
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_permissions import get_permission_breakdown
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.visamodels import AuditLog, Permission, User, UserPermissionOverride

# Org admins may not grant/deny these via per-user overrides.
PLATFORM_ONLY_PERMISSION_CODES = frozenset({
    "admins.super.manage",
    "orgs.view_all",
    "orgs.manage",
    "orgs.switch",
    "admin.data.manage",
    "settings.manage",
    "roles.manage",
    "permissions.manage",
    "subscriptions.manage",
    "subscriptions.view",
    "billing.manage",
    "reports.view_all",
    "reports.export",
    "notifications.view_all",
    "notifications.manage_templates",
    "notifications.manage",
    "visa_types.manage",
})


def assert_org_safe_override_codes(codes: Iterable[str]) -> None:
    blocked = sorted(set(codes) & PLATFORM_ONLY_PERMISSION_CODES)
    if blocked:
        raise ForbiddenException(
            "These permissions are platform-only and cannot be overridden "
            f"in an organization: {', '.join(blocked)}"
        )


async def _get_user_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundException("User not found.")
    return user


async def list_overrides(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    await _get_user_or_404(db, user_id)
    stmt = (
        select(UserPermissionOverride, Permission.code)
        .join(Permission, Permission.id == UserPermissionOverride.permission_id)
        .where(UserPermissionOverride.user_id == user_id)
        .order_by(Permission.code)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "code": code,
            "effect": ov.effect,
            "reason": ov.reason,
            "permission_id": ov.permission_id,
            "actor_id": ov.actor_id,
        }
        for ov, code in rows
    ]


async def replace_overrides(
    db: AsyncSession,
    user_id: uuid.UUID,
    overrides: Iterable[dict],
    actor_id: uuid.UUID,
    *,
    org_scoped: bool = False,
) -> list[dict]:
    await _get_user_or_404(db, user_id)
    overrides = list(overrides)

    # Validate codes exist and no duplicate codes in payload
    codes = [o["code"] for o in overrides]
    if len(codes) != len(set(codes)):
        raise BadRequestException("Duplicate permission codes in overrides payload.")
    if org_scoped:
        assert_org_safe_override_codes(codes)

    perm_map: dict[str, Permission] = {}
    if codes:
        result = await db.execute(select(Permission).where(Permission.code.in_(codes)))
        for p in result.scalars().all():
            perm_map[p.code] = p
        missing = [c for c in codes if c not in perm_map]
        if missing:
            raise BadRequestException(f"Unknown permission codes: {', '.join(missing)}")

    before = await list_overrides(db, user_id)

    await db.execute(
        delete(UserPermissionOverride).where(UserPermissionOverride.user_id == user_id)
    )

    for item in overrides:
        perm = perm_map[item["code"]]
        db.add(
            UserPermissionOverride(
                user_id=user_id,
                permission_id=perm.id,
                effect=item["effect"],
                reason=item.get("reason"),
                actor_id=actor_id,
                created_by=actor_id,
                modified_by=actor_id,
            )
        )

    db.add(
        AuditLog(
            actor_id=actor_id,
            actor_type="user",
            action="rbac.user_overrides.replace",
            resource_type="user",
            resource_id=user_id,
            old_value=json.dumps(before, default=str),
            new_value=json.dumps(overrides, default=str),
            description="Replaced user permission overrides",
            severity="warning",
        )
    )

    await db.commit()
    return await list_overrides(db, user_id)


async def effective_permissions(db: AsyncSession, user_id: uuid.UUID) -> dict:
    await _get_user_or_404(db, user_id)
    breakdown = await get_permission_breakdown(user_id, db)
    return {"user_id": user_id, **breakdown}
