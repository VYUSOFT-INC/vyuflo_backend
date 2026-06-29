# """
# app/api/v1/user_management.py

# User Management endpoints.
# Covers: list, search, get, update, suspend/activate, delete, bulk, profile.

# Mount in main.py:
#     from app.api.v1.user_management import user_management_router
#     app.include_router(user_management_router, prefix="/api/v1", tags=["User Management"])

# Endpoints:
#   GET    /users                         — list all users (paginated + filtered)
#   GET    /users/search                  — search users (lightweight, for dropdowns)
#   GET    /users/{user_id}               — full user detail
#   PATCH  /users/{user_id}               — update basic fields
#   PATCH  /users/{user_id}/status        — suspend or activate
#   DELETE /users/{user_id}               — soft or hard delete
#   POST   /users/bulk                    — bulk suspend/activate/delete
#   GET    /users/{user_id}/profile       — get profile
#   PATCH  /users/{user_id}/profile       — update profile
# """

# from __future__ import annotations

# import uuid
# from typing import Optional

# from fastapi import APIRouter, Query, status

# from app.core.dependencies import Current_User, DBSession
# from app.core.exceptions import ForbiddenException
# from app.core.core_permissions import PermissionChecker
# from app.schemas.user_management import (
#     BulkUserActionRequest,
#     BulkUserActionResponse,
#     BulkUserActionResult,
#     UserDetail,
#     UserListResponse,
#     UserProfileDetail,
#     UserProfileUpdateRequest,
#     UserStatusRequest,
#     UserStatusResponse,
#     UserSummary,
#     UserUpdateRequest,
# )
# from app.services.user_management_service import (
#     service_bulk_user_action,
#     service_delete_user,
#     service_get_user,
#     service_get_user_profile,
#     service_list_users,
#     service_search_users,
#     service_update_user,
#     service_update_user_profile,
#     service_update_user_status,
# )

# user_management_router = APIRouter()

# _require_view_all  = PermissionChecker("users.view_all")
# _require_manage    = PermissionChecker("users.manage")


# # =============================================================================
# # GET /users/search — Search users (lightweight, for dropdowns)
# # MUST be declared BEFORE /users/{user_id} — static path first
# # =============================================================================
# @user_management_router.get(
#     "/users/search",
#     status_code=status.HTTP_200_OK,
#     summary="Search users",
#     description=(
#         "Lightweight search across name and email. "
#         "Returns minimal user fields — safe for dropdowns. "
#         "Used when assigning attorneys to cases, finding users to assign roles, etc."
#     ),
# )
# async def search_users(
#     db:          DBSession,
#     _:           Current_User = _require_view_all,
#     q:           Optional[str]  = Query(None, min_length=2,
#                                         description="Search term — name or email"),
#     role:        Optional[str]  = Query(None, description="Filter by role name"),
#     is_active:   Optional[bool] = Query(None),
#     is_verified: Optional[bool] = Query(None),
#     page:        int            = Query(1,  ge=1),
#     limit:       int            = Query(20, ge=1, le=100),
# ) -> UserListResponse:
#     """
#     Roles allowed:  app_admin, hr, attorney
#     Permission:     users.view_all
#     DB:             SELECT users with optional WHERE + ilike search
#     """
#     result = await service_search_users(
#         db          = db,
#         q           = q,
#         role        = role,
#         is_active   = is_active,
#         is_verified = is_verified,
#         page        = page,
#         limit       = limit,
#     )
#     items = []
#     for u in result["items"]:
#         items.append(UserSummary(
#             id            = u.id,
#             first_name    = u.first_name,
#             last_name     = u.last_name,
#             email         = u.email,
#             phone         = u.phone,
#             is_active     = u.is_active,
#             is_verified   = u.is_verified,
#             roles         = getattr(u, "roles", []),
#             last_login_at = u.last_login_at,
#             created_at    = u.created_at,
#         ))
#     return UserListResponse(
#         items       = items,
#         total       = result["total"],
#         page        = result["page"],
#         limit       = result["limit"],
#         total_pages = result["total_pages"],
#     )


# # =============================================================================
# # POST /users/bulk — Bulk action on multiple users
# # MUST be declared BEFORE /users/{user_id} — static path first
# # =============================================================================
# @user_management_router.post(
#     "/users/bulk",
#     status_code=status.HTTP_200_OK,
#     summary="Bulk user action",
#     description=(
#         "Perform the same action on multiple users at once. "
#         "Actions: `suspend` | `activate` | `delete`. "
#         "Partial success is supported — one failure does not block others. "
#         "Each user result is reported individually."
#     ),
# )
# async def bulk_user_action(
#     payload:      BulkUserActionRequest,
#     db:           DBSession,
#     current_user: Current_User,
#     _:            Current_User = _require_manage,
# ) -> BulkUserActionResponse:
#     """
#     Roles allowed:  app_admin
#     Permission:     users.manage
#     DB:             Multiple UPDATE/DELETE operations, one per user
#     """
#     data = await service_bulk_user_action(
#         db          = db,
#         action      = payload.action,
#         user_ids    = payload.user_ids,
#         reason      = payload.reason,
#         changed_by  = current_user.user_id,
#     )
#     return BulkUserActionResponse(
#         action     = data["action"],
#         processed  = data["processed"],
#         succeeded  = data["succeeded"],
#         failed     = data["failed"],
#         results    = [BulkUserActionResult(**r) for r in data["results"]],
#     )


# # =============================================================================
# # GET /users — List all users
# # =============================================================================
# @user_management_router.get(
#     "/users",
#     status_code=status.HTTP_200_OK,
#     summary="List all users",
#     description=(
#         "Paginated, filterable list of all users. "
#         "Filter by role, active status, verified status. "
#         "Search by name or email. "
#         "Admin and HR can access this."
#     ),
# )
# async def list_users(
#     db:          DBSession,
#     _:           Current_User = _require_view_all,
#     role:        Optional[str]  = Query(None, description="Filter by role name e.g. 'attorney'"),
#     is_active:   Optional[bool] = Query(None, description="Filter by active status"),
#     is_verified: Optional[bool] = Query(None, description="Filter by email verification"),
#     search:      Optional[str]  = Query(None, min_length=2,
#                                         description="Search name or email"),
#     page:        int            = Query(1,  ge=1),
#     limit:       int            = Query(20, ge=1, le=100),
# ) -> UserListResponse:
#     """
#     Roles allowed:  app_admin, hr
#     Permission:     users.view_all
#     DB:             SELECT users with optional WHERE filters + COUNT
#     """
#     result = await service_list_users(
#         db          = db,
#         role        = role,
#         is_active   = is_active,
#         is_verified = is_verified,
#         search      = search,
#         page        = page,
#         limit       = limit,
#     )
#     items = [
#         UserSummary(
#             id            = u.id,
#             first_name    = u.first_name,
#             last_name     = u.last_name,
#             email         = u.email,
#             phone         = u.phone,
#             is_active     = u.is_active,
#             is_verified   = u.is_verified,
#             roles         = getattr(u, "roles", []),
#             last_login_at = u.last_login_at,
#             created_at    = u.created_at,
#         )
#         for u in result["items"]
#     ]
#     return UserListResponse(
#         items       = items,
#         total       = result["total"],
#         page        = result["page"],
#         limit       = result["limit"],
#         total_pages = result["total_pages"],
#     )


# # =============================================================================
# # GET /users/{user_id} — Get single user detail
# # =============================================================================
# @user_management_router.get(
#     "/users/{user_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Get user detail",
#     description=(
#         "Full user detail including profile and roles. "
#         "Admin/HR can view anyone. "
#         "Employee/Attorney can only view their own profile."
#     ),
# )
# async def get_user(
#     user_id:      uuid.UUID,
#     db:           DBSession,
#     current_user: Current_User,
# ) -> UserDetail:
#     """
#     Roles allowed:  app_admin, hr (any user); employee, attorney (own only)
#     Permission:     users.view_all for others; none for own profile
#     Raises:
#       403 — employee trying to view another user's detail
#       404 — user not found
#     """
#     is_own   = current_user.user_id == user_id
#     is_admin = "app_admin" in current_user.roles
#     is_hr    = "hr" in current_user.roles

#     if not is_own and not is_admin and not is_hr:
#         raise ForbiddenException("You can only view your own profile.")

#     user = await service_get_user(db, user_id)

#     profile = getattr(user, "profile", None)
#     profile_out = None
#     if profile:
#         profile_out = UserProfileDetail(
#             full_legal_name      = getattr(profile, "full_legal_name",      None),
#             nationality          = getattr(profile, "nationality",           None),
#             date_of_birth        = getattr(profile, "date_of_birth",         None),
#             gender               = getattr(profile, "gender",                None),
#             country_of_residence = getattr(profile, "country_of_residence",  None),
#             timezone             = getattr(profile, "timezone",              None),
#             preferred_language   = getattr(profile, "preferred_language",    None),
#             profile_picture      = getattr(profile, "profile_picture",       None),
#             onboarding_step      = getattr(profile, "onboarding_step",       1),
#             onboarding_completed = getattr(profile, "onboarding_completed",  False),
#         )

#     return UserDetail(
#         id                = user.id,
#         first_name        = user.first_name,
#         last_name         = user.last_name,
#         email             = user.email,
#         phone             = user.phone,
#         is_active         = user.is_active,
#         is_verified       = user.is_verified,
#         roles             = getattr(user, "roles", []),
#         last_login_at     = user.last_login_at,
#         created_at        = user.created_at,
#         auth_provider     = user.auth_provider,
#         marketing_opt_in  = user.marketing_opt_in,
#         newsletter_opt_in = user.newsletter_opt_in,
#         referral_source   = user.referral_source,
#         country_code      = user.country_code,
#         profile           = profile_out,
#     )


# # =============================================================================
# # PATCH /users/{user_id} — Update basic user fields
# # =============================================================================
# @user_management_router.patch(
#     "/users/{user_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Update user basic info",
#     description=(
#         "Updates basic user fields: name, phone, marketing preferences. "
#         "Admin can update anyone. "
#         "Users can only update their own non-sensitive fields. "
#         "Only provided fields are written — omit a field to leave it unchanged."
#     ),
# )
# async def update_user(
#     user_id:      uuid.UUID,
#     payload:      UserUpdateRequest,
#     db:           DBSession,
#     current_user: Current_User,
# ) -> UserDetail:
#     """
#     Roles allowed:  app_admin (any user); all roles (own profile only)
#     Permission:     users.manage for others; none for self
#     Raises:
#       403 — non-admin trying to update another user
#       404 — user not found
#     """
#     is_own   = current_user.user_id == user_id
#     is_admin = "app_admin" in current_user.roles

#     if not is_own and not is_admin:
#         raise ForbiddenException("You can only update your own profile.")

#     await service_update_user(
#         db                = db,
#         user_id           = user_id,
#         first_name        = payload.first_name,
#         last_name         = payload.last_name,
#         phone             = payload.phone,
#         country_code      = payload.country_code,
#         marketing_opt_in  = payload.marketing_opt_in,
#         newsletter_opt_in = payload.newsletter_opt_in,
#         modified_by       = current_user.user_id,
#     )

#     # Return full detail after update
#     return await get_user(user_id, db, current_user)


# # =============================================================================
# # PATCH /users/{user_id}/status — Suspend or activate
# # =============================================================================
# @user_management_router.patch(
#     "/users/{user_id}/status",
#     status_code=status.HTTP_200_OK,
#     summary="Suspend or activate a user",
#     description=(
#         "Toggles a user's `is_active` flag. "
#         "Suspended users cannot log in — all new login attempts return 403. "
#         "**Blocked** if suspending the last active admin. "
#         "**Blocked** if suspending yourself."
#     ),
# )
# async def update_user_status(
#     user_id:      uuid.UUID,
#     payload:      UserStatusRequest,
#     db:           DBSession,
#     current_user: Current_User,
#     _:            Current_User = _require_manage,
# ) -> UserStatusResponse:
#     """
#     Roles allowed:  app_admin only
#     Permission:     users.manage
#     Raises:
#       400 — self-suspension / last admin guard
#       404 — user not found
#     """
#     data = await service_update_user_status(
#         db         = db,
#         user_id    = user_id,
#         is_active  = payload.is_active,
#         reason     = payload.reason,
#         changed_by = current_user.user_id,
#     )
#     return UserStatusResponse(**data)


# # =============================================================================
# # DELETE /users/{user_id} — Delete user
# # =============================================================================
# @user_management_router.delete(
#     "/users/{user_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Delete a user",
#     description=(
#         "Soft delete (default): sets `is_active=False`. User data is preserved. "
#         "Hard delete (`?hard=true`): permanently removes the user from the DB. "
#         "Hard delete is irreversible — use with caution. "
#         "Cannot delete yourself."
#     ),
# )
# async def delete_user(
#     user_id:      uuid.UUID,
#     db:           DBSession,
#     current_user: Current_User,
#     _:            Current_User = _require_manage,
#     hard:         bool         = Query(False, description="true = permanent deletion"),
# ) -> dict:
#     """
#     Roles allowed:  app_admin
#     Permission:     users.manage
#     Raises:
#       400 — self-deletion / last admin guard
#       404 — user not found
#     """
#     return await service_delete_user(
#         db         = db,
#         user_id    = user_id,
#         deleted_by = current_user.user_id,
#         hard       = hard,
#     )


# # =============================================================================
# # GET /users/{user_id}/profile — Get user profile
# # =============================================================================
# @user_management_router.get(
#     "/users/{user_id}/profile",
#     status_code=status.HTTP_200_OK,
#     summary="Get user profile",
#     description=(
#         "Returns the user_profiles row for a user. "
#         "Admin/HR can view anyone. Users can only view their own."
#     ),
# )
# async def get_user_profile(
#     user_id:      uuid.UUID,
#     db:           DBSession,
#     current_user: Current_User,
# ) -> UserProfileDetail:
#     """
#     Roles allowed:  app_admin, hr (any); employee, attorney (own only)
#     Permission:     users.view_all for others; none for self
#     Raises:
#       403 — non-admin viewing another user's profile
#       404 — user or profile not found
#     """
#     is_own   = current_user.user_id == user_id
#     is_admin = "app_admin" in current_user.roles
#     is_hr    = "hr" in current_user.roles

#     if not is_own and not is_admin and not is_hr:
#         raise ForbiddenException("You can only view your own profile.")

#     profile = await service_get_user_profile(db, user_id)

#     return UserProfileDetail(
#         full_legal_name      = getattr(profile, "full_legal_name",      None),
#         nationality          = getattr(profile, "nationality",           None),
#         date_of_birth        = getattr(profile, "date_of_birth",         None),
#         gender               = getattr(profile, "gender",                None),
#         country_of_residence = getattr(profile, "country_of_residence",  None),
#         timezone             = getattr(profile, "timezone",              None),
#         preferred_language   = getattr(profile, "preferred_language",    None),
#         profile_picture      = getattr(profile, "profile_picture",       None),
#         onboarding_step      = getattr(profile, "onboarding_step",       1),
#         onboarding_completed = getattr(profile, "onboarding_completed",  False),
#     )


# # =============================================================================
# # PATCH /users/{user_id}/profile — Update user profile
# # =============================================================================
# @user_management_router.patch(
#     "/users/{user_id}/profile",
#     status_code=status.HTTP_200_OK,
#     summary="Update user profile",
#     description=(
#         "Updates user_profiles fields: legal name, nationality, DOB, etc. "
#         "Admin can update anyone. Users can only update their own profile. "
#         "Only provided fields are written."
#     ),
# )
# async def update_user_profile(
#     user_id:      uuid.UUID,
#     payload:      UserProfileUpdateRequest,
#     db:           DBSession,
#     current_user: Current_User,
# ) -> UserProfileDetail:
#     """
#     Roles allowed:  app_admin (any user); all roles (own profile only)
#     Raises:
#       403 — non-admin updating another user's profile
#       404 — user or profile not found
#     """
#     is_own   = current_user.user_id == user_id
#     is_admin = "app_admin" in current_user.roles

#     if not is_own and not is_admin:
#         raise ForbiddenException("You can only update your own profile.")

#     profile = await service_update_user_profile(
#         db                   = db,
#         user_id              = user_id,
#         full_legal_name      = payload.full_legal_name,
#         nationality          = payload.nationality,
#         date_of_birth        = str(payload.date_of_birth) if payload.date_of_birth else None,
#         gender               = payload.gender,
#         country_of_residence = payload.country_of_residence,
#         timezone             = payload.timezone,
#         preferred_language   = payload.preferred_language,
#         modified_by          = current_user.user_id,
#     )

#     return UserProfileDetail(
#         full_legal_name      = getattr(profile, "full_legal_name",      None),
#         nationality          = getattr(profile, "nationality",           None),
#         date_of_birth        = getattr(profile, "date_of_birth",         None),
#         gender               = getattr(profile, "gender",                None),
#         country_of_residence = getattr(profile, "country_of_residence",  None),
#         timezone             = getattr(profile, "timezone",              None),
#         preferred_language   = getattr(profile, "preferred_language",    None),
#         profile_picture      = getattr(profile, "profile_picture",       None),
#         onboarding_step      = getattr(profile, "onboarding_step",       1),
#         onboarding_completed = getattr(profile, "onboarding_completed",  False),
#     )
