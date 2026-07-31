"""
app/schemas/system_settings.py  ← FINAL CORRECT VERSION
Replace your existing app/schemas/system_settings.py with this.

Covers all 6 sidebar tabs from the admin General Settings screen:
  General Settings / Security & Access / Integrations /
  Notifications / Feature Flags / Maintenance
"""
from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Must match setting_group_enum in models.py exactly
VALID_GROUPS = {
    "general",        # Platform Identity + Regional & Formatting
    "security",       # Security & Access tab
    "email",          # inside Integrations tab
    "sms",            # inside Integrations tab
    "notifications",  # Notifications tab
    "features",       # Feature Flags tab
    "maintenance",    # Maintenance tab
}
VALID_VALUE_TYPES = {"string", "boolean", "integer", "json", "url"}


# =============================================================================
# Base — shared by Create
# =============================================================================
class SystemSettingBase(BaseModel):
    key:           str  = Field(..., max_length=100,
                                description="Dot-namespaced: 'platform.name', 'features.sms_notifications'")
    value:         str  = Field(..., description="Always stored as string. Cast using value_type on read.")
    value_type:    str  = Field(..., description="string | boolean | integer | json | url")
    setting_group: str  = Field(..., description="general|security|email|sms|notifications|features|maintenance")
    label:         str  = Field(..., max_length=255, description="Admin UI label: 'Platform Name'")
    description:   Optional[str] = Field(None, description="Tooltip text shown in admin UI")
    is_public:     bool = Field(False, description="If True, non-admins can READ this setting")
    is_readonly:   bool = Field(False, description="If True, admin cannot delete this row")
    display_order: int  = Field(0,     description="Sort order within the group tab")

    @field_validator("value_type")
    @classmethod
    def check_value_type(cls, v: str) -> str:
        if v not in VALID_VALUE_TYPES:
            raise ValueError(f"value_type must be one of {VALID_VALUE_TYPES}")
        return v

    @field_validator("setting_group")
    @classmethod
    def check_group(cls, v: str) -> str:
        if v not in VALID_GROUPS:
            raise ValueError(f"setting_group must be one of {VALID_GROUPS}")
        return v


# =============================================================================
# CREATE  (POST /settings)
# =============================================================================
class SystemSettingCreate(SystemSettingBase):
    pass


# =============================================================================
# UPDATE  (PATCH /settings/{key})
# key, value_type, setting_group are intentionally NOT patchable.
# =============================================================================
class SystemSettingUpdate(BaseModel):
    value:         Optional[str]  = None
    label:         Optional[str]  = Field(None, max_length=255)
    description:   Optional[str]  = None
    is_public:     Optional[bool] = None
    is_readonly:   Optional[bool] = None
    display_order: Optional[int]  = None


# =============================================================================
# BULK UPDATE  (PATCH /settings/bulk)
# Used by the "Save Changes" button on the General Settings page.
# Frontend sends all changed fields at once.
# =============================================================================
class SettingValuePatch(BaseModel):
    key:   str = Field(..., max_length=100)
    value: str = Field(..., description="New value as string")


class SystemSettingBulkUpdate(BaseModel):
    updates: List[SettingValuePatch] = Field(..., min_length=1, max_length=100)


# =============================================================================
# FEATURE FLAG TOGGLE  (PATCH /settings/toggle-feature/{key})
# Used by Feature Flags tab toggles
# =============================================================================
class FeatureToggleUpdate(BaseModel):
    enabled: bool


# =============================================================================
# MAINTENANCE MODE  (PATCH /settings/maintenance)
# Used by Maintenance tab
# =============================================================================
class MaintenanceModeUpdate(BaseModel):
    enabled: bool
    message: Optional[str] = Field(None, max_length=500,
                                   description="Banner message shown to users")


# =============================================================================
# RESPONSE
# =============================================================================
class SystemSettingResponse(BaseModel):
    id:            uuid.UUID
    key:           str
    value:         str
    value_type:    str
    setting_group: str
    label:         str
    description:   Optional[str]
    is_public:     bool
    is_readonly:   bool
    display_order: int
    created_at:    datetime
    updated_at:    datetime


    model_config = {"from_attributes": True}

    # def model_post_init(self, __context: Any) -> None:
        # for f in ("created_at", "updated_at"):
            # v = getattr(self, f, None)
            # if v is not None and not isinstance(v, str):
                # object.__setattr__(self, f, str(v))


# =============================================================================
# LIST RESPONSE — grouped dict powers the sidebar tab UI
# GET /settings?group_by=true returns:
#   { "grouped": { "general": [...], "security": [...], ... } }
# =============================================================================
class SystemSettingListResponse(BaseModel):
    items:   List[SystemSettingResponse]
    total:   int
    grouped: Optional[Dict[str, List[SystemSettingResponse]]] = None