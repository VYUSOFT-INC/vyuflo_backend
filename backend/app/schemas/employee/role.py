"""
role.py — Pydantic schemas for Roles & Permissions.

Mirrors the project's existing schema style (Pydantic v2, from_attributes).
Note: `display_name`, `permission_count`, `user_count`, and `roles_assigned`
are NOT columns on the models — the service layer computes them and passes
them in explicitly, so these response models are built by hand (not straight
model_validate on the ORM object).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# PERMISSION
# ===========================================================================

class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             uuid.UUID
    code:           str
    module:         str
    description:    Optional[str] = None
    roles_assigned: List[str] = Field(default_factory=list)  # role names, e.g. ["app_admin", "hr"]
    created_at:     datetime
    updated_at:     Optional[datetime] = None


class PermissionListResponse(BaseModel):
    items:       List[PermissionResponse]
    total:       int
    page:        int
    limit:       int
    total_pages: int


# ===========================================================================
# ROLE
# ===========================================================================

class RoleResponse(BaseModel):
    """Shape used by GET /roles (list item)."""
    id:               uuid.UUID
    name:             str
    display_name:     str
    description:      Optional[str] = None
    is_active:        bool
    permission_count: int
    user_count:       int
    created_at:       datetime
    updated_at:       Optional[datetime] = None


class RoleListResponse(BaseModel):
    items: List[RoleResponse]
    total: int


class RoleDetailResponse(BaseModel):
    """Shape used by GET /roles/{role_id} — role + its permissions."""
    id:               uuid.UUID
    name:             str
    display_name:     str
    description:      Optional[str] = None
    is_active:        bool
    permission_count: int
    user_count:       int
    permissions:      List[PermissionResponse]
    created_at:       datetime
    updated_at:       Optional[datetime] = None


# ===========================================================================
# REQUEST BODIES
# ===========================================================================

class RoleCreate(BaseModel):
    name:        str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)


class RoleUpdate(BaseModel):
    name:        Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)


class AssignPermissionRequest(BaseModel):
    permission_id: uuid.UUID


class BulkPermissionsRequest(BaseModel):
    permission_ids: List[uuid.UUID] = Field(default_factory=list)
