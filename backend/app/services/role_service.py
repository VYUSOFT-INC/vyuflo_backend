"""
role_service.py — Service layer for Roles & Permissions.

Same conventions as application_service.py:
  • Accepts an AsyncSession + validated Pydantic schema / raw params
  • Uses the shared db_* helpers for simple I/O
  • Raises HTTPException with explicit status codes on errors
  • Returns Pydantic response schemas

display_name / permission_count / user_count / roles_assigned are derived
here (they are not columns on the models).
"""

from __future__ import annotations

import math
import uuid
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Project imports  (adjust paths to match your project layout)
# ---------------------------------------------------------------------------
from app.services.services import (
    db_create,
    db_delete,
    db_get_by_field,
    db_get_by_id,
    db_update,
)
from app.models.visamodels import Permission, Role, RolePermission, UserRole
from app.schemas.role import (
    AssignPermissionRequest,
    BulkPermissionsRequest,
    PermissionListResponse,
    PermissionResponse,
    RoleCreate,
    RoleDetailResponse,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
)


# ===========================================================================
# HELPERS
# ===========================================================================

def _display_name(name: str) -> str:
    """app_admin → 'App Admin', hr → 'Hr'."""
    return name.replace("_", " ").title()


async def _assert_role_exists(db: AsyncSession, role_id: uuid.UUID) -> Role:
    role = await db_get_by_id(db, Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found.",
        )
    return role


async def _assert_permission_exists(
    db: AsyncSession, permission_id: uuid.UUID
) -> Permission:
    perm = await db_get_by_id(db, Permission, permission_id)
    if not perm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission {permission_id} not found.",
        )
    return perm


async def _permission_counts(db: AsyncSession) -> Dict[uuid.UUID, int]:
    """{ role_id: number_of_permissions }"""
    rows = await db.execute(
        select(RolePermission.role_id, func.count(RolePermission.id))
        .group_by(RolePermission.role_id)
    )
    return {role_id: count for role_id, count in rows.all()}


async def _user_counts(db: AsyncSession) -> Dict[uuid.UUID, int]:
    """{ role_id: number_of_users }"""
    rows = await db.execute(
        select(UserRole.role_id, func.count(UserRole.id))
        .group_by(UserRole.role_id)
    )
    return {role_id: count for role_id, count in rows.all()}


async def _roles_assigned_map(
    db: AsyncSession,
    permission_ids: Optional[List[uuid.UUID]] = None,
) -> Dict[uuid.UUID, List[str]]:
    """
    { permission_id: [role_name, ...] }
    If permission_ids is given, only those permissions are included.
    """
    stmt = (
        select(RolePermission.permission_id, Role.name)
        .join(Role, Role.id == RolePermission.role_id)
    )
    if permission_ids:
        stmt = stmt.where(RolePermission.permission_id.in_(permission_ids))

    rows = await db.execute(stmt)
    result: Dict[uuid.UUID, List[str]] = {}
    for permission_id, role_name in rows.all():
        result.setdefault(permission_id, []).append(role_name)
    return result


def _build_role_response(
    role: Role,
    perm_counts: Dict[uuid.UUID, int],
    user_counts: Dict[uuid.UUID, int],
) -> RoleResponse:
    return RoleResponse(
        id               = role.id,
        name             = role.name,
        display_name     = _display_name(role.name),
        description      = role.description,
        is_active        = role.is_active,
        permission_count = perm_counts.get(role.id, 0),
        user_count       = user_counts.get(role.id, 0),
        created_at       = role.created_at,
        updated_at       = role.updated_at,
    )


# ===========================================================================
# ROLE — reads
# ===========================================================================

async def list_roles(db: AsyncSession) -> RoleListResponse:
    """GET /roles — all roles with permission/user counts."""
    result = await db.execute(select(Role).order_by(Role.created_at))
    roles = result.scalars().all()

    perm_counts = await _permission_counts(db)
    user_counts = await _user_counts(db)

    items = [_build_role_response(r, perm_counts, user_counts) for r in roles]
    return RoleListResponse(items=items, total=len(items))


async def get_role(db: AsyncSession, role_id: uuid.UUID) -> RoleDetailResponse:
    """GET /roles/{role_id} — role + the permissions assigned to it."""
    role = await _assert_role_exists(db, role_id)

    # permissions assigned to THIS role
    result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.module, Permission.code)
    )
    perms = result.scalars().all()

    perm_ids = [p.id for p in perms]
    assigned = await _roles_assigned_map(db, perm_ids)

    permissions = [
        PermissionResponse(
            id             = p.id,
            code           = p.code,
            module         = p.module,
            description    = p.description,
            roles_assigned = assigned.get(p.id, []),
            created_at     = p.created_at,
            updated_at     = p.updated_at,
        )
        for p in perms
    ]

    user_counts = await _user_counts(db)
    return RoleDetailResponse(
        id               = role.id,
        name             = role.name,
        display_name     = _display_name(role.name),
        description      = role.description,
        is_active        = role.is_active,
        permission_count = len(permissions),
        user_count       = user_counts.get(role.id, 0),
        permissions      = permissions,
        created_at       = role.created_at,
        updated_at       = role.updated_at,
    )


# ===========================================================================
# PERMISSION — reads  (this is what the frontend uses to build the cards)
# ===========================================================================

async def list_permissions(
    db: AsyncSession,
    page: int = 1,
    limit: int = 50,
) -> PermissionListResponse:
    """GET /permissions — master list, each with roles_assigned (role names)."""
    if page < 1:
        page = 1
    if limit < 1:
        limit = 50
    offset = (page - 1) * limit

    # total
    total = (await db.execute(select(func.count(Permission.id)))).scalar_one()

    # page of permissions, grouped by module
    result = await db.execute(
        select(Permission)
        .order_by(Permission.module, Permission.code)
        .limit(limit)
        .offset(offset)
    )
    perms = result.scalars().all()

    assigned = await _roles_assigned_map(db, [p.id for p in perms])

    items = [
        PermissionResponse(
            id             = p.id,
            code           = p.code,
            module         = p.module,
            description    = p.description,
            roles_assigned = assigned.get(p.id, []),
            created_at     = p.created_at,
            updated_at     = p.updated_at,
        )
        for p in perms
    ]

    total_pages = math.ceil(total / limit) if total else 1
    return PermissionListResponse(
        items=items, total=total, page=page, limit=limit, total_pages=total_pages
    )


# ===========================================================================
# ROLE — writes
# ===========================================================================

async def create_role(
    db: AsyncSession,
    payload: RoleCreate,
    current_user_id: uuid.UUID,
) -> RoleResponse:
    """POST /roles — create a custom (non-system) role."""
    existing = await db_get_by_field(db, Role, "name", payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A role named '{payload.name}' already exists.",
        )

    new_role = Role(
        name        = payload.name,
        description = payload.description,
        is_system   = False,
        is_active   = True,
        created_by  = current_user_id,
    )
    new_role = await db_create(db, new_role)
    return _build_role_response(new_role, {}, {})


async def update_role(
    db: AsyncSession,
    role_id: uuid.UUID,
    payload: RoleUpdate,
    current_user_id: uuid.UUID,
) -> RoleResponse:
    """PATCH /roles/{role_id} — update name / description."""
    role = await _assert_role_exists(db, role_id)

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be renamed.",
        )

    data = payload.model_dump(exclude_unset=True)

    # guard duplicate name
    if "name" in data and data["name"] != role.name:
        clash = await db_get_by_field(db, Role, "name", data["name"])
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A role named '{data['name']}' already exists.",
            )

    data["modified_by"] = current_user_id
    updated = await db_update(db, Role, role_id, data)

    perm_counts = await _permission_counts(db)
    user_counts = await _user_counts(db)
    return _build_role_response(updated, perm_counts, user_counts)


async def delete_role(
    db: AsyncSession,
    role_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> dict:
    """DELETE /roles/{role_id} — only custom roles with no users."""
    role = await _assert_role_exists(db, role_id)

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be deleted.",
        )

    user_counts = await _user_counts(db)
    if user_counts.get(role_id, 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This role is still assigned to users. Reassign them first.",
        )

    # role_permissions are removed automatically (cascade="all, delete-orphan")
    deleted = await db_delete(db, Role, role_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found.",
        )
    return {"detail": "Role deleted successfully."}


# ===========================================================================
# ROLE PERMISSIONS — writes (the toggle endpoints)
# ===========================================================================

async def assign_permission(
    db: AsyncSession,
    role_id: uuid.UUID,
    payload: AssignPermissionRequest,
    current_user_id: uuid.UUID,
) -> dict:
    """POST /roles/{role_id}/permissions — turn ONE permission ON (idempotent)."""
    await _assert_role_exists(db, role_id)
    await _assert_permission_exists(db, payload.permission_id)

    # already assigned? → no-op success
    existing = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id       == role_id,
            RolePermission.permission_id == payload.permission_id,
        )
    )
    if existing.scalars().first():
        return {"detail": "Permission already assigned."}

    link = RolePermission(
        role_id       = role_id,
        permission_id = payload.permission_id,
        created_by    = current_user_id,
    )
    await db_create(db, link)
    return {"detail": "Permission assigned."}


async def remove_permission(
    db: AsyncSession,
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> dict:
    """DELETE /roles/{role_id}/permissions/{permission_id} — turn ONE OFF."""
    await _assert_role_exists(db, role_id)

    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id       == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    link = result.scalars().first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This role does not have that permission.",
        )

    await db_delete(db, RolePermission, link.id)
    return {"detail": "Permission removed."}


async def bulk_replace_permissions(
    db: AsyncSession,
    role_id: uuid.UUID,
    payload: BulkPermissionsRequest,
    current_user_id: uuid.UUID,
) -> dict:
    """
    PUT /roles/{role_id}/permissions/bulk
    Replace the role's entire permission set with the given list.
    """
    await _assert_role_exists(db, role_id)

    # validate every incoming permission id exists
    if payload.permission_ids:
        found = await db.execute(
            select(Permission.id).where(Permission.id.in_(payload.permission_ids))
        )
        found_ids = {row[0] for row in found.all()}
        missing = set(payload.permission_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown permission ids: {', '.join(str(m) for m in missing)}",
            )

    # current links
    result = await db.execute(
        select(RolePermission).where(RolePermission.role_id == role_id)
    )
    current_links = result.scalars().all()
    current_ids = {l.permission_id for l in current_links}
    target_ids = set(payload.permission_ids)

    # remove the ones no longer wanted
    for link in current_links:
        if link.permission_id not in target_ids:
            await db_delete(db, RolePermission, link.id)

    # add the new ones
    for perm_id in target_ids - current_ids:
        await db_create(
            db,
            RolePermission(
                role_id       = role_id,
                permission_id = perm_id,
                created_by    = current_user_id,
            ),
        )

    return {"detail": "Permissions updated.", "count": len(target_ids)}
