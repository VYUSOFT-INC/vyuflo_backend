"""
app/routes/system_settings.py  ← FINAL CORRECT VERSION
Replace your existing app/routes/system_settings.py with this.

Covers all sidebar tabs from the admin General Settings screen:
  General Settings / Security & Access / Integrations /
  Notifications / Feature Flags / Maintenance

Endpoints:
  POST   /settings                          — create a new setting key
  GET    /settings                          — list all (pass group_by=true for tab UI)
  GET    /settings/{key}                    — get one by key
  PATCH  /settings/bulk                     — Save Changes button (before /{key})
  PATCH  /settings/toggle-feature/{key}     — Feature Flags tab toggles
  PATCH  /settings/maintenance              — Maintenance tab toggle + banner message
  PATCH  /settings/{key}                    — update single setting
  DELETE /settings/{key}                    — delete (blocked if is_readonly)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, status

from app.core.dependencies import Current_User, DBSession
# from app.core.core_permissions import PermissionChecker
from app.schemas.admin.system_settings import (
    MaintenanceModeUpdate,
    SystemSettingBulkUpdate,
    SystemSettingCreate,
    SystemSettingListResponse,
    SystemSettingResponse,
    SystemSettingUpdate,
)
from app.services.admin.system_settings import (
    service_bulk_update_settings,
    service_create_setting,
    service_delete_setting,
    service_get_setting,
    service_list_settings,
    service_set_maintenance_mode,
    service_toggle_feature,
    service_update_setting,
)

system_settings_router = APIRouter()
# _require = PermissionChecker("settings.manage")


# =============================================================================
# POST /settings — Create new setting key
# =============================================================================
@system_settings_router.post(
    "/settings",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new system setting",
)
async def create_setting(
    payload:      SystemSettingCreate,
    db:           DBSession,
    current_user: Current_User,
    # _:            Current_User = _require,
) -> SystemSettingResponse:
    s = await service_create_setting(
        db=db,
        key=payload.key, value=payload.value, value_type=payload.value_type,
        setting_group=payload.setting_group, label=payload.label,
        description=payload.description, is_public=payload.is_public,
        is_readonly=payload.is_readonly, display_order=payload.display_order,
        created_by=current_user.user_id,
    )
    return SystemSettingResponse.model_validate(s)


# =============================================================================
# GET /settings — List all settings
# group_by=true → returns grouped dict for sidebar tab rendering
# =============================================================================
@system_settings_router.get(
    "/settings",
    status_code=status.HTTP_200_OK,
    summary="List all system settings",
    description=(
        "Pass `group_by=true` to get settings grouped by tab "
        "(general, security, features, etc.) — used by the admin Settings UI. "
        "Non-admins only see is_public=True settings."
    ),
)
async def list_settings(
    db:            DBSession,
    current_user:  Current_User,
    setting_group: Optional[str] = Query(None,  description="Filter by one group tab"),
    group_by:      bool          = Query(False,  description="Return grouped dict for tab UI"),
    search:        Optional[str] = Query(None, min_length=2, description="Search key or label"),
    public_only:   bool          = Query(False,  description="Return only is_public=True settings"),
) -> SystemSettingListResponse:
    is_admin = "app_admin" in current_user.roles
    # is_admin = any(ur.role.name == "app_admin" for ur in current_user.user_roles)

    result = await service_list_settings(
        db=db,
        setting_group=setting_group,
        include_private=is_admin and not public_only,
        group_by=group_by,
        search=search,
    )
    items = [SystemSettingResponse.model_validate(s) for s in result["items"]]
    grouped = None
    if result.get("grouped"):
        grouped = {
            g: [SystemSettingResponse.model_validate(s) for s in vals]
            for g, vals in result["grouped"].items()
        }
    return SystemSettingListResponse(items=items, total=result["total"], grouped=grouped)


# =============================================================================
# PATCH /settings/bulk — "Save Changes" button
# MUST be declared BEFORE /settings/{key} to avoid FastAPI
# treating "bulk" as a key parameter value
# =============================================================================
@system_settings_router.patch(
    "/settings/bulk",
    status_code=status.HTTP_200_OK,
    summary="Bulk update multiple settings",
    description="Saves all changed fields on the settings page in one transaction.",
)
async def bulk_update_settings(
    payload:      SystemSettingBulkUpdate,
    db:           DBSession,
    current_user: Current_User,
    # _:            Current_User = _require,
) -> dict:
    updated = await service_bulk_update_settings(
        db=db,
        updates=[u.model_dump() for u in payload.updates],
        modified_by=current_user.user_id,
    )
    return {
        "message":       f"{len(updated)} setting(s) updated.",
        "updated_count": len(updated),
        "keys":          [s.key for s in updated],
    }


# =============================================================================
# PATCH /settings/toggle-feature/{key} — Feature Flags tab toggle switches
# MUST be declared BEFORE /settings/{key}
# =============================================================================
@system_settings_router.patch(
    "/settings/toggle-feature/{key}",
    status_code=status.HTTP_200_OK,
    summary="Toggle a boolean feature flag",
    description=(
        "Enables or disables any boolean setting. "
        "Used by Feature Flags tab on/off switches. "
        "Change is immediate — no restart needed."
    ),
)
async def toggle_feature(
    key:          str,
    enabled:      bool,
    db:           DBSession,
    current_user: Current_User,
    # _:            Current_User = _require,
) -> SystemSettingResponse:
    s = await service_toggle_feature(
        db=db, key=key, enabled=enabled, modified_by=current_user.user_id
    )
    return SystemSettingResponse.model_validate(s)


# =============================================================================
# PATCH /settings/maintenance — Maintenance tab
# MUST be declared BEFORE /settings/{key}
# =============================================================================
@system_settings_router.patch(
    "/settings/maintenance",
    status_code=status.HTTP_200_OK,
    summary="Toggle maintenance mode",
    description=(
        "Enables or disables platform maintenance mode. "
        "When enabled, all non-admin API requests return 503. "
        "Optionally update the banner message shown to users."
    ),
)
async def set_maintenance_mode(
    payload:      MaintenanceModeUpdate,
    db:           DBSession,
    current_user: Current_User,
    # _:            Current_User = _require,
) -> dict:
    return await service_set_maintenance_mode(
        db=db, enabled=payload.enabled,
        message=payload.message, modified_by=current_user.user_id,
    )


# =============================================================================
# GET /settings/{key} — Get one setting by key
# =============================================================================
@system_settings_router.get(
    "/settings/{key}",
    status_code=status.HTTP_200_OK,
    summary="Get a single setting by key",
)
async def get_setting(
    key:          str,
    db:           DBSession,
    current_user: Current_User,
) -> SystemSettingResponse:
    s = await service_get_setting(db, key)
    is_admin = "app_admin" in current_user.roles
    # is_admin = any(ur.role.name == "app_admin" for ur in current_user.user_roles)
    if not is_admin and not s.is_public:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("You do not have permission to view this setting.")
    return SystemSettingResponse.model_validate(s)


# =============================================================================
# PATCH /settings/{key} — Update a single setting
# =============================================================================
@system_settings_router.patch(
    "/settings/{key}",
    status_code=status.HTTP_200_OK,
    summary="Update a single system setting",
)
async def update_setting(
    key:          str,
    payload:      SystemSettingUpdate,
    db:           DBSession,
    current_user: Current_User,
    # _:            Current_User = _require,
) -> SystemSettingResponse:
    s = await service_update_setting(
        db=db, key=key, value=payload.value, label=payload.label,
        description=payload.description, is_public=payload.is_public,
        is_readonly=payload.is_readonly, display_order=payload.display_order,
        modified_by=current_user.user_id,
    )
    return SystemSettingResponse.model_validate(s)


# =============================================================================
# DELETE /settings/{key} — Delete a setting
# =============================================================================
@system_settings_router.delete(
    "/settings/{key}",
    status_code=status.HTTP_200_OK,
    summary="Delete a system setting",
    description="Blocked if is_readonly=True.",
)
async def delete_setting(
    key:          str,
    db:           DBSession,
    current_user: Current_User,
    # _:            Current_User = _require,
) -> dict:
    return await service_delete_setting(db, key)