"""Schemas for /admin/organizations and super-admin management."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class OrganizationCreateRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=300)
    industry: Optional[str] = None
    website: Optional[str] = None
    domain: Optional[str] = None
    # Optional first org admin
    admin_email: Optional[EmailStr] = None
    admin_name: Optional[str] = None
    admin_password: Optional[str] = Field(None, min_length=8)


class OrganizationUpdateRequest(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1, max_length=300)
    industry: Optional[str] = None
    website: Optional[str] = None
    domain: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class OrganizationAdminCreateRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=200)
    password: Optional[str] = Field(None, min_length=8)


class SuperAdminCreateRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=8)


class OrganizationMemberItem(BaseModel):
    user_id: str
    email: str
    name: str
    org_role: str
    is_active: bool


class OrganizationListItem(BaseModel):
    id: str
    company_name: str
    industry: Optional[str] = None
    is_active: bool
    is_verified: bool
    member_count: int = 0
    admin_count: int = 0
    owner_email: Optional[str] = None
    created_at: Optional[datetime] = None


class OrganizationDetail(OrganizationListItem):
    website: Optional[str] = None
    domain: Optional[str] = None
    members: list[OrganizationMemberItem] = Field(default_factory=list)


class OrganizationListResponse(BaseModel):
    items: list[OrganizationListItem]
    total: int


class SwitchOrganizationRequest(BaseModel):
    organization_id: uuid.UUID


class SwitchOrganizationResponse(BaseModel):
    access_token: str
    active_organization_id: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
