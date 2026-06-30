"""
roles.py — API routes for Roles & Permissions.

Exposes everything the admin "Roles & Permissions" screen calls:

    GET    /roles
    GET    /roles/{role_id}
    GET    /permissions
    POST   /roles
    PATCH  /roles/{role_id}
    DELETE /roles/{role_id}
    POST   /roles/{role_id}/permissions
    DELETE /roles/{role_id}/permissions/{permission_id}
    PUT    /roles/{role_id}/permissions/bulk

⚠️ ADJUST THESE TWO IMPORTS to match your project's actual dependency module.
   `get_db`           → yields an AsyncSession
   `get_current_user` → returns the authenticated user object (must have .id)
   (Your other routers already import these — copy the exact path from one of
    them, e.g. application router.)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User                  # ⚠️ ADJUST if your user model differs
from app.services.employee import role_service
from app.schemas.employee.role import (
    AssignPermissionRequest,
    BulkPermissionsRequest,
    PermissionListResponse,
    RoleCreate,
    RoleDetailResponse,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
)

roles_router = APIRouter(tags=["Roles & Permissions"])


# ===========================================================================
# READS
# ===========================================================================

@roles_router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await role_service.list_roles(db)


@roles_router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await role_service.list_permissions(db, page=page, limit=limit)


@roles_router.get("/roles/{role_id}", response_model=RoleDetailResponse)
async def get_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await role_service.get_role(db, role_id)


# ===========================================================================
# ROLE WRITES
# ===========================================================================

@roles_router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await role_service.create_role(db, payload, current_user.user_id)


@roles_router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await role_service.update_role(db, role_id, payload, current_user.user_id)


@roles_router.delete("/roles/{role_id}")
async def delete_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await role_service.delete_role(db, role_id, current_user.user_id)


# ===========================================================================
# ROLE-PERMISSION WRITES  (toggles)
# ===========================================================================

@roles_router.post("/roles/{role_id}/permissions")
async def assign_permission(
    role_id: uuid.UUID,
    payload: AssignPermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await role_service.assign_permission(db, role_id, payload, current_user.user_id)


@roles_router.delete("/roles/{role_id}/permissions/{permission_id}")
async def remove_permission(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await role_service.remove_permission(db, role_id, permission_id, current_user.user_id)


@roles_router.put("/roles/{role_id}/permissions/bulk")
async def bulk_replace_permissions(
    role_id: uuid.UUID,
    payload: BulkPermissionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await role_service.bulk_replace_permissions(db, role_id, payload, current_user.user_id)
