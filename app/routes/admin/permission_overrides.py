"""
Per-user RBAC override routes (P1).

    GET  /api/v1/users/{id}/permission-overrides
    PUT  /api/v1/users/{id}/permission-overrides
    GET  /api/v1/users/{id}/effective-permissions
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.core.core_permissions import PermissionChecker
from app.core.dependencies import CurrentUserData, DBSession
from app.schemas.admin.permission_overrides import (
    EffectivePermissionsResponse,
    PermissionOverrideResponse,
    PermissionOverridesListResponse,
    PermissionOverridesPutRequest,
)
from app.services.admin.permission_override_service import (
    effective_permissions,
    list_overrides,
    replace_overrides,
)

permission_overrides_router = APIRouter(tags=["RBAC — User Overrides"])


@permission_overrides_router.get(
    "/users/{user_id}/permission-overrides",
    response_model=PermissionOverridesListResponse,
    summary="List permission overrides for a user",
)
async def get_user_permission_overrides(
    user_id: uuid.UUID,
    db: DBSession,
    _: CurrentUserData = Depends(PermissionChecker("permissions.manage")),
) -> PermissionOverridesListResponse:
    items = await list_overrides(db, user_id)
    return PermissionOverridesListResponse(
        user_id=user_id,
        overrides=[PermissionOverrideResponse(**i) for i in items],
    )


@permission_overrides_router.put(
    "/users/{user_id}/permission-overrides",
    response_model=PermissionOverridesListResponse,
    summary="Replace all permission overrides for a user",
)
async def put_user_permission_overrides(
    user_id: uuid.UUID,
    body: PermissionOverridesPutRequest,
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("permissions.manage")),
) -> PermissionOverridesListResponse:
    items = await replace_overrides(
        db,
        user_id,
        [o.model_dump() for o in body.overrides],
        actor_id=current_user.user_id,
    )
    return PermissionOverridesListResponse(
        user_id=user_id,
        overrides=[PermissionOverrideResponse(**i) for i in items],
    )


@permission_overrides_router.get(
    "/users/{user_id}/effective-permissions",
    response_model=EffectivePermissionsResponse,
    summary="Effective permissions breakdown (role / allow / deny / effective)",
)
async def get_user_effective_permissions(
    user_id: uuid.UUID,
    db: DBSession,
    _: CurrentUserData = Depends(PermissionChecker("permissions.manage")),
) -> EffectivePermissionsResponse:
    data = await effective_permissions(db, user_id)
    return EffectivePermissionsResponse(**data)
