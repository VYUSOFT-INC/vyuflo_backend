"""Schemas for per-user RBAC permission overrides (P1)."""
from __future__ import annotations

from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PermissionOverrideItem(BaseModel):
    code: str = Field(..., description="Permission code, e.g. applications.create")
    effect: Literal["allow", "deny"]
    reason: Optional[str] = Field(None, max_length=500)


class PermissionOverridesPutRequest(BaseModel):
    """Full replace of the user's override set."""
    overrides: List[PermissionOverrideItem] = Field(default_factory=list)


class PermissionOverrideResponse(BaseModel):
    code: str
    effect: Literal["allow", "deny"]
    reason: Optional[str] = None
    permission_id: UUID
    actor_id: Optional[UUID] = None


class PermissionOverridesListResponse(BaseModel):
    user_id: UUID
    overrides: List[PermissionOverrideResponse]


class EffectivePermissionsResponse(BaseModel):
    user_id: UUID
    role: List[str]
    allow: List[str]
    deny: List[str]
    effective: List[str]
