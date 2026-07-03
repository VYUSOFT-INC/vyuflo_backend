"""
app/schemas/user_management.py

Pydantic v2 schemas for:
  - Custom Role CRUD
  - User Management (list, get, update, suspend, delete, bulk)
  - User Profile management
  - User search & filters

Follows your existing style:
  - ConfigDict(from_attributes=True) for ORM objects
  - Optional fields default to None
  - All UUIDs as uuid.UUID
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

RESERVED_ROLE_NAMES = {"app_admin", "hr", "employee", "attorney"}

# =============================================================================
# CUSTOM ROLE schemas
# =============================================================================

class CustomRoleCreate(BaseModel):
    """
    POST /roles/custom
    Creates a brand-new role with a free-text name.
    Different from the 4 predefined roles — no enum restriction.
    """
    name:        str = Field(..., min_length=2, max_length=100,
                             description="Role name e.g. 'senior_attorney', 'compliance_officer'")
    description: Optional[str] = Field(None, max_length=255)

    @field_validator("name")
    @classmethod
    # def validate_name(cls, v: str) -> str:
    #     v = v.strip().lower().replace(" ", "_")

    #     # Only allow alphanumeric + underscores
    #     if not re.match(r"^[a-z][a-z0-9_]{1,99}$", v):
    #         raise ValueError("Role name must be lowercase letters, numbers, underscores only.")

    #     return v
    def name_clean(cls, v: str) -> str:
        # Lowercase, strip spaces, replace spaces with underscores
        cleaned = v.strip().lower().replace(" ", "_")
        # Block names that clash with predefined roles
        reserved = {"app_admin", "hr", "attorney", "employee"}
        if cleaned in reserved:
            raise ValueError(
                f"'{cleaned}' is a predefined system role and cannot be recreated as a custom role."
            )
        return cleaned


# class CustomRoleUpdate(BaseModel):
#     """
#     PATCH /roles/custom/{role_id}
#     Only description and is_active are mutable after creation.
#     Name is immutable once set — changing it would break all existing
#     user_roles rows referencing this role.
#     """
#     description: Optional[str] = Field(None, max_length=255)
#     is_active:   Optional[bool] = None


# class CustomRoleResponse(BaseModel):
#     """Returned by all custom role endpoints."""
#     model_config = ConfigDict(from_attributes=True)

#     id:               uuid.UUID
#     name:             str
#     description:      Optional[str]
#     is_active:        bool
#     is_custom:        bool = True     # always True — distinguishes from predefined
#     permission_count: int  = 0
#     user_count:       int  = 0
#     created_at:       datetime
#     updated_at:       datetime


# class CustomRoleListResponse(BaseModel):
#     items: list[CustomRoleResponse]
#     total: int


# # =============================================================================
# # USER MANAGEMENT schemas
# # =============================================================================

# class UserSummary(BaseModel):
#     """
#     Lightweight user — used in list/search endpoints.
#     Never includes sensitive fields like password_hash.
#     """
#     model_config = ConfigDict(from_attributes=True)

#     id:           uuid.UUID
#     first_name:   str
#     last_name:    str
#     email:        str
#     phone:        Optional[str]
#     is_active:    bool
#     is_verified:  bool
#     roles:        list[str] = []        # populated by service, not ORM
#     last_login_at: Optional[datetime]
#     created_at:   datetime


# class UserDetail(UserSummary):
#     """
#     Full user detail — used in GET /users/{user_id}.
#     Includes profile fields and role details.
#     """
#     auth_provider:     str
#     marketing_opt_in:  bool
#     newsletter_opt_in: bool
#     referral_source:   Optional[str]
#     country_code:      Optional[str]
#     profile:           Optional[UserProfileDetail] = None


# class UserProfileDetail(BaseModel):
#     """Nested inside UserDetail."""
#     model_config = ConfigDict(from_attributes=True)

#     full_legal_name:      Optional[str]
#     nationality:          Optional[str]
#     date_of_birth:        Optional[date]
#     gender:               Optional[str]
#     country_of_residence: Optional[str]
#     timezone:             Optional[str]
#     preferred_language:   Optional[str]
#     profile_picture:      Optional[str]
#     onboarding_step:      int  = 1
#     onboarding_completed: bool = False


# class UserListResponse(BaseModel):
#     """Paginated user list with optional stats."""
#     items:       list[UserSummary]
#     total:       int
#     page:        int
#     limit:       int
#     total_pages: int


# class UserUpdateRequest(BaseModel):
#     """
#     PATCH /users/{user_id}
#     Admin can update any user. User can update own non-sensitive fields.
#     All fields optional — only provided fields are written.
#     """
#     first_name:       Optional[str] = Field(None, min_length=1, max_length=100)
#     last_name:        Optional[str] = Field(None, min_length=1, max_length=100)
#     phone:            Optional[str] = Field(None, max_length=20)
#     country_code:     Optional[str] = Field(None, max_length=10)
#     marketing_opt_in: Optional[bool] = None
#     newsletter_opt_in: Optional[bool] = None


# class UserStatusRequest(BaseModel):
#     """
#     PATCH /users/{user_id}/status
#     Dedicated suspend/activate endpoint — separate from general update
#     because it has important side effects (session invalidation).
#     """
#     is_active: bool
#     reason:    Optional[str] = Field(
#         None, max_length=500,
#         description="Reason for suspension — stored in audit log"
#     )


# class UserStatusResponse(BaseModel):
#     user_id:      uuid.UUID
#     is_active:    bool
#     changed_by:   uuid.UUID
#     reason:       Optional[str]
#     changed_at:   datetime


# class UserProfileUpdateRequest(BaseModel):
#     """PATCH /users/{user_id}/profile"""
#     full_legal_name:      Optional[str] = Field(None, max_length=200)
#     nationality:          Optional[str] = Field(None, max_length=100)
#     date_of_birth:        Optional[date] = None
#     gender:               Optional[str] = Field(None, max_length=20)
#     country_of_residence: Optional[str] = Field(None, max_length=100)
#     timezone:             Optional[str] = Field(None, max_length=50)
#     preferred_language:   Optional[str] = Field(None, max_length=10)


# class BulkUserActionRequest(BaseModel):
#     """
#     POST /users/bulk
#     Perform the same action on multiple users at once.
#     """
#     action:   str = Field(..., description="suspend | activate | delete")
#     user_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)
#     reason:   Optional[str]   = Field(None, max_length=500)

#     @field_validator("action")
#     @classmethod
#     def validate_action(cls, v: str) -> str:
#         allowed = {"suspend", "activate", "delete"}
#         if v not in allowed:
#             raise ValueError(f"action must be one of: {', '.join(allowed)}")
#         return v


# class BulkUserActionResult(BaseModel):
#     user_id: uuid.UUID
#     status:  str               # "success" | "failed"
#     reason:  Optional[str]     # only populated on failure


# class BulkUserActionResponse(BaseModel):
#     action:     str
#     processed:  int
#     succeeded:  int
#     failed:     int
#     results:    list[BulkUserActionResult]


# class UserSearchParams(BaseModel):
#     """Query params for GET /users/search — used as a typed helper."""
#     q:           Optional[str]  = None   # search term
#     role:        Optional[str]  = None   # filter by role name
#     is_active:   Optional[bool] = None
#     is_verified: Optional[bool] = None
#     page:        int = Field(1,  ge=1)
#     limit:       int = Field(20, ge=1, le=100)


# # Fix forward reference
# UserDetail.model_rebuild()
