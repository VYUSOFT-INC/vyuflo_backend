"""
/admin/organizations — super_admin org tenancy management
POST /admin/super-admins — create platform super admins

When a super admin has entered an organization (active_organization_id),
they cannot list or manage other organizations / their admins.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.core_permissions import PermissionChecker
from app.core.dependencies import CurrentUserData, DBSession
from app.core.exceptions import ForbiddenException
from app.core.org_scope import (
    assert_not_switched_away_from_org,
    is_platform_admin,
    resolve_effective_organization_id,
)
from app.schemas.admin.organizations import (
    OrganizationAdminCreateRequest,
    OrganizationCreateRequest,
    OrganizationDetail,
    OrganizationListResponse,
    OrganizationUpdateRequest,
    SuperAdminCreateRequest,
)
from app.services.admin import organization_service as svc

organizations_router = APIRouter(prefix="/admin", tags=["Admin — Organizations"])


def _require_global_org_console(current_user: CurrentUserData, db=None) -> None:
    """Block org-directory mutations while entered into an org."""
    active = getattr(current_user, "active_organization_id", None)
    if active and is_platform_admin(current_user.roles):
        raise ForbiddenException(
            "Exit the current organization before managing other organizations."
        )


@organizations_router.get("/organizations", response_model=OrganizationListResponse)
async def list_organizations(
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("orgs.view_all")),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    active_org = await resolve_effective_organization_id(db, current_user)
    # Entered into an org → only that org (no other orgs / their admins)
    if active_org is not None:
        detail = await svc.service_get_organization(db, active_org)
        item = {
            "id": detail["id"],
            "company_name": detail["company_name"],
            "industry": detail.get("industry"),
            "is_active": detail["is_active"],
            "is_verified": detail["is_verified"],
            "member_count": detail.get("member_count", 0),
            "admin_count": detail.get("admin_count", 0),
            "owner_email": detail.get("owner_email"),
            "created_at": detail.get("created_at"),
        }
        return OrganizationListResponse(items=[item], total=1)

    data = await svc.service_list_organizations(db, search=search, page=page, limit=limit)
    return OrganizationListResponse(items=data["items"], total=data["total"])


@organizations_router.post(
    "/organizations",
    response_model=OrganizationDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    body: OrganizationCreateRequest,
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("orgs.manage")),
):
    _require_global_org_console(current_user)
    return await svc.service_create_organization(
        db,
        company_name=body.company_name,
        industry=body.industry,
        website=body.website,
        domain=body.domain,
        admin_email=body.admin_email,
        admin_name=body.admin_name,
        admin_password=body.admin_password,
        created_by=current_user.user_id,
    )


@organizations_router.get("/organizations/{org_id}", response_model=OrganizationDetail)
async def get_organization(
    org_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("orgs.view_all")),
):
    await assert_not_switched_away_from_org(db, current_user, org_id)
    active_org = await resolve_effective_organization_id(db, current_user)
    if active_org is not None and active_org != org_id:
        raise ForbiddenException("You can only view the organization you entered.")
    return await svc.service_get_organization(db, org_id)


@organizations_router.patch("/organizations/{org_id}", response_model=OrganizationDetail)
async def update_organization(
    org_id: uuid.UUID,
    body: OrganizationUpdateRequest,
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("orgs.manage")),
):
    await assert_not_switched_away_from_org(db, current_user, org_id)
    return await svc.service_update_organization(
        db,
        org_id,
        company_name=body.company_name,
        industry=body.industry,
        website=body.website,
        domain=body.domain,
        is_active=body.is_active,
        is_verified=body.is_verified,
        modified_by=current_user.user_id,
    )


@organizations_router.post("/organizations/{org_id}/admins", response_model=OrganizationDetail)
async def add_org_admin(
    org_id: uuid.UUID,
    body: OrganizationAdminCreateRequest,
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("orgs.manage")),
):
    await assert_not_switched_away_from_org(db, current_user, org_id)
    return await svc.service_add_org_admin(
        db,
        org_id,
        email=body.email,
        name=body.name,
        password=body.password,
        created_by=current_user.user_id,
    )


@organizations_router.delete(
    "/organizations/{org_id}/admins/{user_id}",
    response_model=OrganizationDetail,
)
async def remove_org_admin(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("orgs.manage")),
):
    await assert_not_switched_away_from_org(db, current_user, org_id)
    return await svc.service_remove_org_admin(
        db, org_id, user_id, modified_by=current_user.user_id,
    )


@organizations_router.post("/super-admins", status_code=status.HTTP_201_CREATED)
async def create_super_admin(
    body: SuperAdminCreateRequest,
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("admins.super.manage")),
):
    _require_global_org_console(current_user)
    return await svc.service_create_super_admin(
        db,
        email=body.email,
        name=body.name,
        password=body.password,
        created_by=current_user.user_id,
    )
