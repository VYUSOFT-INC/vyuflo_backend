"""
app/routes/admin/user_management.py

Admin User Management endpoints — spec section A.
Mounted in main.py as:
    app.include_router(user_management_router, prefix="/api/v1")
Resolves to /api/v1/admin/users*

Role values are NATIVE to this DB (hr | app_admin | employee | attorney) —
the admin/lawyer rename was intentionally skipped; frontend normalises.

Endpoints (spec §A2):
    GET    /admin/users
    GET    /admin/users/stats
    GET    /admin/users/export
    GET    /admin/users/{id}
    POST   /admin/users
    PUT    /admin/users/{id}
    PUT    /admin/users/{id}/role
    PUT    /admin/users/{id}/status
    DELETE /admin/users/{id}
    POST   /admin/users/bulk-role
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.core_permissions import PermissionChecker
from app.core.dependencies import Current_User, DBSession
from app.core.exceptions import BadRequestException, ForbiddenException
from app.core.org_scope import (
    assert_user_in_active_org,
    is_platform_admin,
    require_list_organization_id,
    resolve_effective_organization_id,
    upsert_organization_member,
)
from app.schemas.admin.user_management import (
    AdminBulkRoleRequest,
    AdminBulkRoleResponse,
    AdminResetPasswordRequest,
    AdminResetPasswordResponse,
    AdminUserCreateRequest,
    AdminUserItem,
    AdminUserListResponse,
    AdminUserRoleUpdateRequest,
    AdminUserStatusUpdateRequest,
    AdminUserUpdateRequest,
    UserStatsResponse,
)
from app.services.admin.user_management_service import (
    service_admin_reset_password,
    service_bulk_set_role,
    service_create_admin_user,
    service_delete_admin_user,
    service_export_admin_users_csv,
    service_get_admin_user,
    service_get_admin_user_stats,
    service_list_admin_users,
    service_update_admin_user,
    service_update_admin_user_role,
    service_update_admin_user_status,
)

user_management_router = APIRouter(prefix="/admin", tags=["Admin — User Management"])

_require_view_all = PermissionChecker("users.view_all")
_require_manage    = PermissionChecker("users.manage")

PLATFORM_ONLY_ROLES = frozenset({"super_admin", "app_admin"})


def _normalize_role_name(role: str) -> str:
    r = (role or "").strip().lower()
    if r in ("admin", "app_admin"):
        return "super_admin"
    if r == "lawyer":
        return "attorney"
    return r


async def _reject_platform_role_in_org_context(
    db,
    current_user: Current_User,
    role: Optional[str],
) -> str | None:
    """Block assigning Super Admin when org-scoped (entered org or org_admin caller)."""
    if role is None:
        return None
    normalized = _normalize_role_name(role)
    org_id = await resolve_effective_organization_id(db, current_user)
    in_org_scope = org_id is not None or (
        "org_admin" in (current_user.roles or []) and not is_platform_admin(current_user.roles)
    )
    if in_org_scope and normalized in PLATFORM_ONLY_ROLES:
        raise ForbiddenException(
            "Cannot assign Super Admin from an organization context."
        )
    return normalized


# =============================================================================
# GET /admin/users/stats — MUST be declared before /users/{id}
# =============================================================================
@user_management_router.get(
    "/users/stats",
    response_model=UserStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin user KPI cards",
)
async def get_user_stats(
    db: DBSession,
    current_user: Current_User = _require_view_all,
) -> UserStatsResponse:
    scoped_org = await require_list_organization_id(db, current_user)
    data = await service_get_admin_user_stats(db, organization_id=scoped_org)
    return UserStatsResponse(**data)


# =============================================================================
# GET /admin/users/export — MUST be declared before /users/{id}
# =============================================================================
@user_management_router.get(
    "/users/export",
    status_code=status.HTTP_200_OK,
    summary="Export users as CSV",
)
async def export_users(
    db: DBSession,
    current_user: Current_User = _require_view_all,
    search: Optional[str] = Query(None),
    role:   Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
) -> Response:
    scoped_org = await require_list_organization_id(db, current_user)
    csv_text = await service_export_admin_users_csv(
        db=db, search=search, role=role, status_filter=status_filter,
        organization_id=scoped_org,
    )
    filename = "users-export.csv"
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# POST /admin/users/bulk-role — MUST be declared before /users/{id}
# =============================================================================
@user_management_router.post(
    "/users/bulk-role",
    response_model=AdminBulkRoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk set role for multiple users",
)
async def bulk_set_role(
    payload: AdminBulkRoleRequest,
    db: DBSession,
    current_user: Current_User,
    _: Current_User = _require_manage,
) -> AdminBulkRoleResponse:
    role = await _reject_platform_role_in_org_context(db, current_user, payload.role)
    user_ids = [uuid.UUID(uid) for uid in payload.userIds]
    for uid in user_ids:
        await assert_user_in_active_org(db, current_user, uid)
    data = await service_bulk_set_role(
        db=db,
        user_ids=user_ids,
        role=role or payload.role,
        changed_by=current_user.user_id,
    )
    return AdminBulkRoleResponse(**data)


# =============================================================================
# GET /admin/users — list all users
# =============================================================================
@user_management_router.get(
    "/users",
    response_model=AdminUserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all users (paginated + filtered)",
)
async def list_users(
    db: DBSession,
    current_user: Current_User = _require_view_all,
    search: Optional[str] = Query(None),
    role:   Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page:   int = Query(1, ge=1),
    limit:  int = Query(20, ge=1, le=100),
) -> AdminUserListResponse:
    scoped_org = await require_list_organization_id(db, current_user)

    result = await service_list_admin_users(
        db=db, search=search, role=role, status_filter=status_filter,
        page=page, limit=limit,
        organization_id=scoped_org,
        hide_platform_users=True,
    )
    return AdminUserListResponse(
        users=[AdminUserItem(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
        totalPages=result["total_pages"],
    )


# =============================================================================
# GET /admin/users/{id} — single user detail
# =============================================================================
@user_management_router.get(
    "/users/{user_id}",
    response_model=AdminUserItem,
    status_code=status.HTTP_200_OK,
    summary="Get single user detail",
)
async def get_user(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: Current_User = _require_view_all,
) -> AdminUserItem:
    from app.core.org_scope import assert_user_in_active_org
    await assert_user_in_active_org(db, current_user, user_id)
    data = await service_get_admin_user(db, user_id)
    return AdminUserItem(**data)


# =============================================================================
# POST /admin/users — create user
# =============================================================================
@user_management_router.post(
    "/users",
    response_model=AdminUserItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(
    payload: AdminUserCreateRequest,
    db: DBSession,
    current_user: Current_User,
    _: Current_User = _require_manage,
    _rbac=Depends(PermissionChecker("users.manage")),
) -> AdminUserItem:
    role = await _reject_platform_role_in_org_context(db, current_user, payload.role)
    data = await service_create_admin_user(
        db=db,
        name=payload.name,
        email=payload.email,
        role=role or payload.role,
        company=payload.company,
        password=payload.password,
        created_by=current_user.user_id,
    )
    # If org-scoped, attach new user as org member
    org_id = await resolve_effective_organization_id(db, current_user)
    if org_id is not None:
        org_role = role if role in ("org_admin", "hr", "employee", "attorney") else "employee"
        await upsert_organization_member(
            db,
            employer_profile_id=org_id,
            user_id=uuid.UUID(data["id"]),
            org_role=org_role,
            changed_by=current_user.user_id,
        )
        await db.commit()
        data = await service_get_admin_user(db, uuid.UUID(data["id"]))
    return AdminUserItem(**data)


# =============================================================================
# PUT /admin/users/{id} — update user
# =============================================================================
@user_management_router.put(
    "/users/{user_id}",
    response_model=AdminUserItem,
    status_code=status.HTTP_200_OK,
    summary="Update a user",
)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdateRequest,
    db: DBSession,
    current_user: Current_User,
    _: Current_User = _require_manage,
    _rbac=Depends(PermissionChecker("users.manage")),
) -> AdminUserItem:
    await assert_user_in_active_org(db, current_user, user_id)
    role = await _reject_platform_role_in_org_context(db, current_user, payload.role)
    data = await service_update_admin_user(
        db=db,
        user_id=user_id,
        name=payload.name,
        email=payload.email,
        role=role if payload.role is not None else None,
        company=payload.company,
        modified_by=current_user.user_id,
    )
    return AdminUserItem(**data)


# =============================================================================
# PUT /admin/users/{id}/role — change role
# =============================================================================
@user_management_router.put(
    "/users/{user_id}/role",
    response_model=AdminUserItem,
    status_code=status.HTTP_200_OK,
    summary="Change a user's role",
)
async def update_user_role(
    user_id: uuid.UUID,
    payload: AdminUserRoleUpdateRequest,
    db: DBSession,
    current_user: Current_User,
    _: Current_User = _require_manage,
    _rbac=Depends(PermissionChecker("users.manage")),
) -> AdminUserItem:
    await assert_user_in_active_org(db, current_user, user_id)
    role = await _reject_platform_role_in_org_context(db, current_user, payload.role)
    data = await service_update_admin_user_role(
        db=db, user_id=user_id, role=role or payload.role, changed_by=current_user.user_id,
    )
    return AdminUserItem(**data)


# =============================================================================
# PUT /admin/users/{id}/status — suspend / activate
# =============================================================================
@user_management_router.put(
    "/users/{user_id}/status",
    response_model=AdminUserItem,
    status_code=status.HTTP_200_OK,
    summary="Suspend or activate a user",
)
async def update_user_status(
    user_id: uuid.UUID,
    payload: AdminUserStatusUpdateRequest,
    db: DBSession,
    current_user: Current_User,
    _: Current_User = _require_manage,
    _rbac=Depends(PermissionChecker("users.manage")),
) -> AdminUserItem:
    await assert_user_in_active_org(db, current_user, user_id)
    data = await service_update_admin_user_status(
        db=db, user_id=user_id, status_value=payload.status, changed_by=current_user.user_id,
    )
    return AdminUserItem(**data)


# =============================================================================
# DELETE /admin/users/{id} — delete
# =============================================================================
@user_management_router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a user (soft by default, ?hard=true for permanent)",
)
async def delete_user(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: Current_User,
    _: Current_User = _require_manage,
    hard: bool = Query(False),
    _rbac=Depends(PermissionChecker("users.manage")),
) -> dict:
    await assert_user_in_active_org(db, current_user, user_id)
    return await service_delete_admin_user(
        db=db, user_id=user_id, deleted_by=current_user.user_id, hard=hard,
    )


# =============================================================================
# POST /admin/users/{user_id}/reset-password
# =============================================================================
@user_management_router.post(
    "/users/{user_id}/reset-password",
    response_model=AdminResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin reset a user's password",
    description=(
        "Requires users.manage. "
        "If temporary_password is omitted and send_email=true, triggers the "
        "existing password-reset OTP email flow. "
        "If temporary_password is provided, hashes and sets it; may still email."
    ),
)
async def admin_reset_password(
    user_id: uuid.UUID,
    payload: AdminResetPasswordRequest,
    db: DBSession,
    current_user: Current_User,
    _: Current_User = _require_manage,
    _rbac=Depends(PermissionChecker("users.manage")),
) -> AdminResetPasswordResponse:
    await assert_user_in_active_org(db, current_user, user_id)
    data = await service_admin_reset_password(
        db,
        user_id=user_id,
        send_email=payload.send_email,
        temporary_password=payload.temporary_password,
        actor_id=current_user.user_id,
    )
    return AdminResetPasswordResponse(**data)
