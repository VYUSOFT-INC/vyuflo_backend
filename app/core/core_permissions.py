"""
app/core/permissions.py

Dynamic RBAC permission checker.

Drop-in Depends() for any route that needs permission enforcement.
Permissions are always re-fetched from the database so any runtime
role/permission change is reflected on the very next request — no
hardcoded permission strings in route logic, no token re-issue required
for sensitive write operations.

Usage
-----
# Require a single permission (most common):
@router.get("/admin/users")
async def list_users(
    db: DBSession,
    current_user: Annotated[CurrentUserData, Depends(PermissionChecker("users.view_all"))],
):
    ...

# Require ALL of multiple permissions:
Depends(PermissionChecker(["roles.manage", "permissions.manage"]))

# Require ANY ONE of multiple permissions:
Depends(PermissionChecker(["applications.view_all", "applications.view_own"], require_all=False))

# Pre-built aliases (import and use directly):
AdminOnly        = Depends(RoleChecker(["app_admin"]))
AdminOrHR        = Depends(RoleChecker(["app_admin", "hr"]))
"""

from typing import Annotated, Union
import uuid

from fastapi import Depends
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUserData, get_current_user
from app.core.exceptions import ForbiddenException

# ── lazy imports to avoid circular deps ──────────────────────────────────────
# Models are imported inside functions / at module level carefully.
# If your models live in app.models.models, adjust the import path.


# =============================================================================
# CORE — fetch effective permissions from DB
# =============================================================================

async def get_effective_permissions(
    user_id: uuid.UUID,
    db: AsyncSession,
) -> set[str]:
    """
    Traverses the full RBAC chain in ONE query:
        user → user_roles → roles → role_permissions → permissions

    Returns a set of permission code strings, e.g.:
        {"applications.create", "documents.verify", "users.view_all"}

    Called on every permission-guarded request so changes to
    role_permissions are reflected immediately without token re-issue.
    """
    # Import here to avoid circular imports at module load time
    from app.models.models import UserRole, Role, RolePermission, Permission

    stmt = (
        select(distinct(Permission.code))
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role,           Role.id == RolePermission.role_id)
        .join(UserRole,       UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            Role.is_active   == True,
        )
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.fetchall()}


async def get_user_roles_from_db(
    user_id: uuid.UUID,
    db: AsyncSession,
) -> set[str]:
    """Returns the set of role name strings currently assigned to the user."""
    from app.models.models import UserRole, Role

    stmt = (
        select(distinct(Role.name))
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            Role.is_active   == True,
        )
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.fetchall()}


# =============================================================================
# PermissionChecker — factory dependency
# =============================================================================

class PermissionChecker:
    """
    Reusable FastAPI dependency that enforces permission requirements.

    Every call re-queries the database so permission changes made by
    admins take effect immediately — no token invalidation needed.

    Parameters
    ----------
    required : str | list[str]
        One permission code or a list of codes.
    require_all : bool
        True  → user must have ALL listed permissions (default).
        False → user must have AT LEAST ONE listed permission.
    """

    def __init__(
        self,
        required: Union[str, list[str]],
        require_all: bool = True,
    ):
        if isinstance(required, str):
            required = [required]
        self.required     = required
        self.require_all  = require_all

    async def __call__(
        self,
        db:           AsyncSession  = Depends(get_db),
        current_user: CurrentUserData = Depends(get_current_user),
    ) -> CurrentUserData:
        """
        Returns the current user if permission check passes.
        Raises ForbiddenException otherwise.
        """
        effective = await get_effective_permissions(current_user.user_id, db)

        if self.require_all:
            missing = [p for p in self.required if p not in effective]
            if missing:
                raise ForbiddenException(
                    f"Permission denied. Missing: {', '.join(missing)}"
                )
        else:
            if not any(p in effective for p in self.required):
                raise ForbiddenException(
                    f"Permission denied. Need one of: {', '.join(self.required)}"
                )

        return current_user


# =============================================================================
# RoleChecker — lighter check when role is sufficient
# =============================================================================

class RoleChecker:
    """
    Dependency that checks the user's roles from the JWT payload.
    Use when a role check is sufficient and a DB round-trip is not needed.

    Example: Depends(RoleChecker(["app_admin"]))
    """

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        current_user: CurrentUserData = Depends(get_current_user),
    ) -> CurrentUserData:
        if not any(r in current_user.roles for r in self.allowed_roles):
            raise ForbiddenException(
                f"Role required: one of {', '.join(self.allowed_roles)}"
            )
        return current_user


# =============================================================================
# Pre-built dependency aliases — import these in routers directly
# =============================================================================

# Role-based (JWT, no DB hit)
AdminOnly  = Annotated[CurrentUserData, Depends(RoleChecker(["app_admin"]))]
AdminOrHR  = Annotated[CurrentUserData, Depends(RoleChecker(["app_admin", "hr"]))]

# Permission-based (DB hit — always fresh)
CanManageUsers       = Annotated[CurrentUserData, Depends(PermissionChecker("users.manage"))]
CanViewAllUsers      = Annotated[CurrentUserData, Depends(PermissionChecker("users.view_all"))]
CanManageRoles       = Annotated[CurrentUserData, Depends(PermissionChecker("roles.manage"))]
CanManagePermissions = Annotated[CurrentUserData, Depends(PermissionChecker("permissions.manage"))]
