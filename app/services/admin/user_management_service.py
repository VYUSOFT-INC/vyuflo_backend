"""
app/services/user_management_service.py

Business logic for:
  - Custom Role CRUD (create / update / delete custom roles)
  - User Management (list, get, update, suspend, delete, bulk, search)
  - User Profile management

All functions are async SQLAlchemy.
Raises exceptions from app.core.exceptions — never returns error dicts.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.models.visamodels import (
    Permission,
    Role,
    RolePermission,
    User,
    UserProfile,
    UserRole,
)


# =============================================================================
# CUSTOM ROLES — service functions
# =============================================================================

# The 4 system roles that can never be deleted or renamed
SYSTEM_ROLES = {"app_admin", "hr", "attorney", "employee"}


async def service_create_custom_role(
    db:          AsyncSession,
    name:        str,
    description: Optional[str],
    created_by:  uuid.UUID,
) -> Role:
    """
    Creates a new custom role with a free-text name.

    Guards:
    - Name cannot clash with the 4 predefined system roles
    - Name must be unique across ALL roles (system + custom)
    - DB column must be String type, not Enum
      (run migration before using this — see MIGRATION NOTE below)

    MIGRATION NOTE:
    Before this service works, you must change Role.name from:
        Column(Enum("app_admin","hr","attorney","employee"), ...)
    To:
        Column(String(100), nullable=False, unique=True)
    And run: alembic revision --autogenerate -m "role_name_string"
             alembic upgrade head
    Also add is_custom column:
        Column(Boolean, default=False, nullable=False)
    """
    # Block system role names
    if name in SYSTEM_ROLES:
        raise BadRequestException(
            f"'{name}' is a predefined system role and cannot be created as a custom role."
        )

    # Check name uniqueness across ALL roles
    existing = (
        await db.execute(select(Role).where(Role.name == name))
    ).scalar_one_or_none()
    if existing:
        raise ConflictException(f"A role with name '{name}' already exists.")

    role = Role(
        id          = uuid.uuid4(),
        name        = name,
        description = description,
        is_active   = True,
        is_custom   = True,       # marks this as admin-created, not seeded
        created_by  = created_by,
        modified_by = created_by,
    )
    db.add(role)
    await db.flush()
    await db.refresh(role)

    # Attach counts for response
    role.permission_count = 0  # type: ignore[attr-defined]
    role.user_count       = 0  # type: ignore[attr-defined]
    return role


# async def service_list_custom_roles(
#     db:          AsyncSession,
#     include_all: bool = False,    # True → include system roles too
# ) -> list[dict]:
#     """
#     Lists roles.
#     include_all=False → custom roles only (is_custom=True)
#     include_all=True  → all roles including predefined system roles
#     """
#     stmt = select(Role)
#     if not include_all:
#         stmt = stmt.where(Role.is_custom == True)
#     stmt = stmt.order_by(Role.name)

#     roles = (await db.execute(stmt)).scalars().all()

#     output = []
#     for role in roles:
#         perm_count = (
#             await db.execute(
#                 select(func.count()).where(RolePermission.role_id == role.id)
#             )
#         ).scalar_one()

#         user_count = (
#             await db.execute(
#                 select(func.count())
#                 .join(User, User.id == UserRole.user_id)
#                 .where(UserRole.role_id == role.id, User.is_active == True)
#             )
#         ).scalar_one()

#         output.append({
#             **{c.key: getattr(role, c.key) for c in role.__table__.columns},
#             "permission_count": perm_count,
#             "user_count":       user_count,
#             "is_custom":        getattr(role, "is_custom", True),
#         })

#     return output


# async def service_get_custom_role(
#     db:      AsyncSession,
#     role_id: uuid.UUID,
# ) -> dict:
#     """Get a single custom role by ID with permission + user counts."""
#     role = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
#     if not role:
#         raise NotFoundException(f"Role '{role_id}' not found.")

#     perm_count = (
#         await db.execute(
#             select(func.count()).where(RolePermission.role_id == role_id)
#         )
#     ).scalar_one()

#     user_count = (
#         await db.execute(
#             select(func.count())
#             .join(User, User.id == UserRole.user_id)
#             .where(UserRole.role_id == role_id, User.is_active == True)
#         )
#     ).scalar_one()

#     return {
#         **{c.key: getattr(role, c.key) for c in role.__table__.columns},
#         "permission_count": perm_count,
#         "user_count":       user_count,
#         "is_custom":        getattr(role, "is_custom", True),
#     }


# async def service_update_custom_role(
#     db:          AsyncSession,
#     role_id:     uuid.UUID,
#     description: Optional[str],
#     is_active:   Optional[bool],
#     modified_by: uuid.UUID,
# ) -> dict:
#     """
#     Updates description and/or is_active on a custom role.
#     Name is immutable after creation.
#     System roles can also be updated via this — only description/is_active.
#     """
#     role = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
#     if not role:
#         raise NotFoundException(f"Role '{role_id}' not found.")

#     # Cannot deactivate a system role that has active users
#     if is_active is False and role.name in SYSTEM_ROLES:
#         admin_users = (
#             await db.execute(
#                 select(func.count())
#                 .join(User, User.id == UserRole.user_id)
#                 .where(UserRole.role_id == role_id, User.is_active == True)
#             )
#         ).scalar_one()
#         if admin_users > 0:
#             raise BadRequestException(
#                 f"Cannot deactivate system role '{role.name}' while {admin_users} active user(s) hold it."
#             )

#     if description is not None:
#         role.description = description
#     if is_active is not None:
#         role.is_active = is_active

#     role.modified_by = modified_by
#     await db.flush()

#     return await service_get_custom_role(db, role_id)


# async def service_delete_custom_role(
#     db:      AsyncSession,
#     role_id: uuid.UUID,
# ) -> dict:
#     """
#     Deletes a custom role.

#     Guards:
#     1. Cannot delete system roles (app_admin, hr, attorney, employee)
#     2. Cannot delete a role that is currently assigned to any user
#        — would leave those users with broken role assignments
#     """
#     role = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
#     if not role:
#         raise NotFoundException(f"Role '{role_id}' not found.")

#     # Guard 1: system roles are protected
#     if role.name in SYSTEM_ROLES:
#         raise BadRequestException(
#             f"Cannot delete system role '{role.name}'. System roles are permanent."
#         )

#     # Guard 2: cannot delete if users hold this role
#     user_count = (
#         await db.execute(
#             select(func.count()).where(UserRole.role_id == role_id)
#         )
#     ).scalar_one()
#     if user_count > 0:
#         raise BadRequestException(
#             f"Cannot delete role '{role.name}' — {user_count} user(s) currently hold it. "
#             "Reassign them first."
#         )

#     # Delete role_permissions first (FK constraint)
#     await db.execute(
#         delete(RolePermission).where(RolePermission.role_id == role_id)
#     )
#     await db.delete(role)
#     await db.flush()

#     return {"message": f"Custom role '{role.name}' deleted successfully."}


# # =============================================================================
# # USER MANAGEMENT — service functions
# # =============================================================================

# async def service_list_users(
#     db:          AsyncSession,
#     role:        Optional[str],
#     is_active:   Optional[bool],
#     is_verified: Optional[bool],
#     search:      Optional[str],
#     page:        int,
#     limit:       int,
# ) -> dict:
#     """
#     Paginated, filterable list of all users.
#     Enriches each user with their role names.
#     """
#     stmt = select(User)

#     # Filters
#     if is_active is not None:
#         stmt = stmt.where(User.is_active == is_active)
#     if is_verified is not None:
#         stmt = stmt.where(User.is_verified == is_verified)
#     if search:
#         pattern = f"%{search}%"
#         stmt = stmt.where(
#             or_(
#                 User.first_name.ilike(pattern),
#                 User.last_name.ilike(pattern),
#                 User.email.ilike(pattern),
#             )
#         )
#     if role:
#         # Filter by role name — join through user_roles → roles
#         stmt = stmt.join(UserRole, UserRole.user_id == User.id).join(
#             Role, Role.id == UserRole.role_id
#         ).where(Role.name == role)

#     # Count total
#     count_stmt = select(func.count()).select_from(stmt.subquery())
#     total = (await db.execute(count_stmt)).scalar_one()

#     # Paginate
#     offset = (page - 1) * limit
#     stmt   = stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
#     users  = (await db.execute(stmt)).scalars().all()

#     # Enrich with role names
#     user_ids = [u.id for u in users]
#     role_map: dict[uuid.UUID, list[str]] = {u.id: [] for u in users}

#     if user_ids:
#         role_stmt = (
#             select(UserRole.user_id, Role.name)
#             .join(Role, Role.id == UserRole.role_id)
#             .where(UserRole.user_id.in_(user_ids))
#         )
#         for row in (await db.execute(role_stmt)).fetchall():
#             role_map[row[0]].append(row[1])

#     # Attach roles as transient attribute
#     for u in users:
#         u.roles = role_map[u.id]  # type: ignore[attr-defined]

#     return {
#         "items":       users,
#         "total":       total,
#         "page":        page,
#         "limit":       limit,
#         "total_pages": math.ceil(total / limit) if limit else 1,
#     }


# async def service_get_user(
#     db:      AsyncSession,
#     user_id: uuid.UUID,
# ) -> User:
#     """Get a single user with their profile and roles."""
#     user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
#     if not user:
#         raise NotFoundException(f"User '{user_id}' not found.")

#     # Attach roles
#     role_stmt = (
#         select(Role.name)
#         .join(UserRole, UserRole.role_id == Role.id)
#         .where(UserRole.user_id == user_id)
#     )
#     user.roles = (await db.execute(role_stmt)).scalars().all()  # type: ignore[attr-defined]

#     # Attach profile
#     profile = (
#         await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
#     ).scalar_one_or_none()
#     user.profile = profile  # type: ignore[attr-defined]

#     return user


# async def service_update_user(
#     db:               AsyncSession,
#     user_id:          uuid.UUID,
#     first_name:       Optional[str],
#     last_name:        Optional[str],
#     phone:            Optional[str],
#     country_code:     Optional[str],
#     marketing_opt_in: Optional[bool],
#     newsletter_opt_in: Optional[bool],
#     modified_by:      uuid.UUID,
# ) -> User:
#     """Updates basic user fields. Only provided (non-None) fields are written."""
#     user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
#     if not user:
#         raise NotFoundException(f"User '{user_id}' not found.")

#     if first_name       is not None: user.first_name        = first_name
#     if last_name        is not None: user.last_name         = last_name
#     if phone            is not None: user.phone             = phone
#     if country_code     is not None: user.country_code      = country_code
#     if marketing_opt_in is not None: user.marketing_opt_in  = marketing_opt_in
#     if newsletter_opt_in is not None: user.newsletter_opt_in = newsletter_opt_in

#     user.modified_by = modified_by
#     await db.flush()
#     await db.refresh(user)
#     return await service_get_user(db, user_id)


# async def service_update_user_status(
#     db:         AsyncSession,
#     user_id:    uuid.UUID,
#     is_active:  bool,
#     reason:     Optional[str],
#     changed_by: uuid.UUID,
# ) -> dict:
#     """
#     Suspend or activate a user.

#     Guards:
#     1. Cannot suspend yourself
#     2. Cannot suspend the last active app_admin
#     """
#     user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
#     if not user:
#         raise NotFoundException(f"User '{user_id}' not found.")

#     # Guard 1: cannot suspend yourself
#     if str(user_id) == str(changed_by) and not is_active:
#         raise BadRequestException("You cannot suspend your own account.")

#     # Guard 2: if suspending an admin, ensure at least one other active admin exists
#     if not is_active:
#         admin_role = (
#             await db.execute(select(Role).where(Role.name == "app_admin"))
#         ).scalar_one_or_none()

#         if admin_role:
#             is_admin_user = (
#                 await db.execute(
#                     select(func.count()).where(
#                         and_(UserRole.user_id == user_id, UserRole.role_id == admin_role.id)
#                     )
#                 )
#             ).scalar_one()

#             if is_admin_user:
#                 other_admins = (
#                     await db.execute(
#                         select(func.count())
#                         .join(User, User.id == UserRole.user_id)
#                         .where(
#                             UserRole.role_id == admin_role.id,
#                             User.is_active   == True,
#                             User.id          != user_id,
#                         )
#                     )
#                 ).scalar_one()
#                 if other_admins == 0:
#                     raise BadRequestException(
#                         "Cannot suspend the last active admin in the system."
#                     )

#     user.is_active   = is_active
#     user.modified_by = changed_by
#     await db.flush()

#     return {
#         "user_id":    user_id,
#         "is_active":  is_active,
#         "changed_by": changed_by,
#         "reason":     reason,
#         "changed_at": datetime.now(timezone.utc),
#     }


# async def service_delete_user(
#     db:         AsyncSession,
#     user_id:    uuid.UUID,
#     deleted_by: uuid.UUID,
#     hard:       bool = False,
# ) -> dict:
#     """
#     Soft delete (default): sets is_active=False.
#     Hard delete (?hard=true): removes user from DB.
#     Hard delete is blocked if user has active applications.
#     """
#     user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
#     if not user:
#         raise NotFoundException(f"User '{user_id}' not found.")

#     if str(user_id) == str(deleted_by):
#         raise BadRequestException("You cannot delete your own account.")

#     if hard:
#         # Block hard delete if user has data (import Application model if needed)
#         # For now, just delete — add application check when Application model confirmed
#         await db.delete(user)
#         await db.flush()
#         return {"message": f"User '{user.email}' permanently deleted."}
#     else:
#         user.is_active   = False
#         user.modified_by = deleted_by
#         await db.flush()
#         return {"message": f"User '{user.email}' deactivated (soft delete)."}


# async def service_search_users(
#     db:          AsyncSession,
#     q:           Optional[str],
#     role:        Optional[str],
#     is_active:   Optional[bool],
#     is_verified: Optional[bool],
#     page:        int,
#     limit:       int,
# ) -> dict:
#     """
#     Full-text search across name and email.
#     Used for admin dropdowns (assign attorney to case, etc.)
#     Returns lightweight user objects — no sensitive fields.
#     """
#     return await service_list_users(
#         db          = db,
#         role        = role,
#         is_active   = is_active,
#         is_verified = is_verified,
#         search      = q,
#         page        = page,
#         limit       = limit,
#     )


# async def service_bulk_user_action(
#     db:         AsyncSession,
#     action:     str,
#     user_ids:   list[uuid.UUID],
#     reason:     Optional[str],
#     changed_by: uuid.UUID,
# ) -> dict:
#     """
#     Performs suspend / activate / delete on multiple users.
#     Processes each user individually so one failure doesn't
#     block the rest — partial success is reported.
#     """
#     results = []
#     succeeded = 0
#     failed    = 0

#     for uid in user_ids:
#         try:
#             if action == "suspend":
#                 await service_update_user_status(
#                     db, uid, is_active=False,
#                     reason=reason, changed_by=changed_by
#                 )
#             elif action == "activate":
#                 await service_update_user_status(
#                     db, uid, is_active=True,
#                     reason=reason, changed_by=changed_by
#                 )
#             elif action == "delete":
#                 await service_delete_user(db, uid, deleted_by=changed_by, hard=False)

#             results.append({"user_id": uid, "status": "success", "reason": None})
#             succeeded += 1

#         except Exception as e:
#             results.append({"user_id": uid, "status": "failed", "reason": str(e)})
#             failed += 1
#             # Rollback only this user — continue with next
#             await db.rollback()

#     return {
#         "action":    action,
#         "processed": len(user_ids),
#         "succeeded": succeeded,
#         "failed":    failed,
#         "results":   results,
#     }


# async def service_get_user_profile(
#     db:      AsyncSession,
#     user_id: uuid.UUID,
# ) -> UserProfile:
#     """Get the user_profiles row for a user."""
#     # Verify user exists first
#     user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
#     if not user:
#         raise NotFoundException(f"User '{user_id}' not found.")

#     profile = (
#         await db.execute(
#             select(UserProfile).where(UserProfile.user_id == user_id)
#         )
#     ).scalar_one_or_none()

#     if not profile:
#         raise NotFoundException(f"Profile not found for user '{user_id}'.")

#     return profile


# async def service_update_user_profile(
#     db:                   AsyncSession,
#     user_id:              uuid.UUID,
#     full_legal_name:      Optional[str],
#     nationality:          Optional[str],
#     date_of_birth:        Optional[str],
#     gender:               Optional[str],
#     country_of_residence: Optional[str],
#     timezone:             Optional[str],
#     preferred_language:   Optional[str],
#     modified_by:          uuid.UUID,
# ) -> UserProfile:
#     """Updates user_profiles fields. Only provided fields are written."""
#     profile = (
#         await db.execute(
#             select(UserProfile).where(UserProfile.user_id == user_id)
#         )
#     ).scalar_one_or_none()

#     if not profile:
#         raise NotFoundException(f"Profile not found for user '{user_id}'.")

#     if full_legal_name      is not None: profile.full_legal_name      = full_legal_name
#     if nationality          is not None: profile.nationality          = nationality
#     if date_of_birth        is not None: profile.date_of_birth        = date_of_birth
#     if gender               is not None: profile.gender               = gender
#     if country_of_residence is not None: profile.country_of_residence = country_of_residence
#     if timezone             is not None: profile.timezone             = timezone
#     if preferred_language   is not None: profile.preferred_language   = preferred_language

#     profile.modified_by = modified_by
#     await db.flush()
#     await db.refresh(profile)
#     return profile
