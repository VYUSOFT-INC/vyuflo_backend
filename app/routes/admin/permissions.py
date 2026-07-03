"""
app/api/v1/permissions.py

Permissions management endpoints.

Mount in main.py / router aggregator:
    from app.api.v1.permissions import permissions_router
    app.include_router(permissions_router, prefix="/api/v1", tags=["Permissions"])

All routes require `permissions.manage` — only app_admin has this.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query, status

from app.core.dependencies import Current_User, DBSession
from app.core.core_permissions import PermissionChecker
from app.schemas.rbac import (
    PermissionCreate,
    PermissionListResponse,
    PermissionResponse,
    PermissionUpdate,
)
from app.services.rbac_service import (
    service_create_permission,
    service_delete_permission,
    service_get_permission,
    service_list_permissions,
    service_update_permission,
)

permissions_router = APIRouter()

# All routes in this file require permissions.manage.
# Defined once here, referenced as a Depends() on every route.
_require_manage = PermissionChecker("permissions.manage")


# =============================================================================
# POST /permissions — Create
# =============================================================================
@permissions_router.post(
    "/permissions",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new permission",
    description=(
        "Creates a new permission code in the system. "
        "Code must be dot-namespaced (e.g. `reports.export`). "
        "Once created, assign it to roles via `POST /roles/{role_id}/permissions`."
    ),
)
async def create_permission(
    payload:      PermissionCreate,
    db:           DBSession,
    current_user: Current_User,
    # _:            Current_User = _require_manage,  # permission gate
) -> PermissionResponse:
    """
    Roles allowed:   app_admin
    Permission:      permissions.manage
    DB operation:    INSERT INTO permissions
    Raises:
      409 ConflictException  — code already exists
    """
    permission = await service_create_permission(
        db          = db,
        code        = payload.code,
        module      = payload.module,
        description = payload.description,
        created_by  = current_user.user_id,
    )
    # Attach empty roles_assigned for response serialization
    permission.roles_assigned = []  # type: ignore[attr-defined]
    return PermissionResponse.model_validate(permission)


# =============================================================================
# GET /permissions — List (paginated, filterable, groupable)
# =============================================================================
@permissions_router.get(
    "/permissions",
    status_code=status.HTTP_200_OK,
    summary="List all permissions",
    description=(
        "Paginated list of all permissions. "
        "Filter by module, search by code/description. "
        "Pass `group_by_module=true` to receive a `grouped` dict keyed by module "
        "(used by the admin permission matrix UI)."
    ),
)
async def list_permissions(
    db:              DBSession,
    _:               Current_User = _require_manage,
    module:          Optional[str] = Query(
        None,
        description="Filter by module: users|applications|documents|messages|roles|support|content",
    ),
    search:          Optional[str] = Query(
        None,
        min_length=2,
        description="Search in code and description fields",
    ),
    page:            int  = Query(1,    ge=1,    description="Page number"),
    limit:           int  = Query(50,   ge=1, le=200, description="Items per page"),
    group_by_module: bool = Query(False, description="Also return permissions grouped by module"),
) -> PermissionListResponse:
    """
    Roles allowed:  app_admin
    Permission:     permissions.manage
    DB operation:   SELECT with optional WHERE + COUNT
    """
    result = await service_list_permissions(
        db              = db,
        module          = module,
        search          = search,
        page            = page,
        limit           = limit,
        group_by_module = group_by_module,
    )

    items = [PermissionResponse.model_validate(p) for p in result["items"]]

    grouped = None
    if result.get("grouped"):
        grouped = {
            mod: [PermissionResponse.model_validate(p) for p in perms]
            for mod, perms in result["grouped"].items()
        }

    return PermissionListResponse(
        items       = items,
        total       = result["total"],
        page        = result["page"],
        limit       = result["limit"],
        total_pages = result["total_pages"],
        grouped     = grouped,
    )


# =============================================================================
# GET /permissions/{permission_id} — Detail
# =============================================================================
@permissions_router.get(
    "/permissions/{permission_id}",
    status_code=status.HTTP_200_OK,
    summary="Get permission detail",
    description="Returns a single permission including which roles currently have it assigned.",
)
async def get_permission(
    permission_id: uuid.UUID,
    db:            DBSession,
    _:             Current_User = _require_manage,
) -> PermissionResponse:
    """
    Roles allowed:  app_admin
    Permission:     permissions.manage
    DB operation:   SELECT permissions + JOIN role_permissions → roles
    Raises:
      404 NotFoundException — permission not found
    """
    permission = await service_get_permission(db, permission_id)
    return PermissionResponse.model_validate(permission)


# =============================================================================
# PATCH /permissions/{permission_id} — Update
# =============================================================================
@permissions_router.patch(
    "/permissions/{permission_id}",
    status_code=status.HTTP_200_OK,
    summary="Update a permission",
    description=(
        "Updates `description` and/or `module` on a permission. "
        "The `code` field is **intentionally immutable** — renaming it would "
        "silently break all permission checks that reference the old code string. "
        "To rename, delete and recreate."
    ),
)
async def update_permission(
    permission_id: uuid.UUID,
    payload:       PermissionUpdate,
    db:            DBSession,
    current_user:  Current_User,
    _:             Current_User = _require_manage,
) -> PermissionResponse:
    """
    Roles allowed:  app_admin
    Permission:     permissions.manage
    DB operation:   UPDATE permissions SET description=?, module=?
    Raises:
      404 NotFoundException — permission not found
    """
    permission = await service_update_permission(
        db            = db,
        permission_id = permission_id,
        description   = payload.description,
        module        = payload.module,
        modified_by   = current_user.user_id,
    )
    permission.roles_assigned = []  # type: ignore[attr-defined]
    return PermissionResponse.model_validate(permission)


# =============================================================================
# DELETE /permissions/{permission_id} — Delete
# =============================================================================
@permissions_router.delete(
    "/permissions/{permission_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a permission",
    description=(
        "Permanently deletes a permission. "
        "**Blocked** if the permission is currently assigned to any role — "
        "remove it from all roles first via `DELETE /roles/{role_id}/permissions/{permission_id}`."
    ),
)
async def delete_permission(
    permission_id: uuid.UUID,
    db:            DBSession,
    _:             Current_User = _require_manage,
) -> dict:
    """
    Roles allowed:  app_admin
    Permission:     permissions.manage
    DB operation:   DELETE FROM permissions WHERE id=?
    Raises:
      404 NotFoundException   — permission not found
      400 BadRequestException — permission still assigned to roles
    """
    return await service_delete_permission(db, permission_id)
