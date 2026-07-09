"""
app/api/v1/custom_roles.py

Custom Role management endpoints.
These are admin-created roles beyond the 4 predefined system roles.

Mount in main.py:
    from app.api.v1.custom_roles import custom_roles_router
    app.include_router(custom_roles_router, prefix="/api/v1", tags=["Custom Roles"])

Endpoints:
  POST   /roles/custom                  — create a new custom role
  GET    /roles/custom                  — list custom roles only
  GET    /roles/all                     — list ALL roles (system + custom)
  GET    /roles/custom/{role_id}        — get custom role detail
  PATCH  /roles/custom/{role_id}        — update name/description/is_active
  DELETE /roles/custom/{role_id}        — delete (blocked if users assigned)

IMPORTANT — MIGRATION REQUIRED BEFORE USING:
  The Role.name column must be changed from Postgres enum to String.
  See MIGRATION_GUIDE at the bottom of this file.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

import app
from app.core.dependencies import Current_User, DBSession
# from app.core.core_permissions import PermissionChecker
# import app.schemas.user_management
from app.services.admin.user_management_service import (
    service_create_custom_role,
    # service_delete_custom_role,
    # service_get_custom_role,
    # service_list_custom_roles,
    # service_update_custom_role,
)
from app.schemas.admin.user_management import CustomRoleCreate

custom_roles_router = APIRouter()

# _require_roles_manage = PermissionChecker("roles.manage")


# =============================================================================
# POST /roles/custom — Create a custom role
# MUST be declared before /roles/custom/{role_id} — path order matters
# =============================================================================
@custom_roles_router.post(
    "/roles/custom",
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom role",
    description=(
        "Creates a brand-new role with any name the admin chooses. "
        "Name must be unique and cannot clash with the 4 system roles "
        "(app_admin, hr, attorney, employee). "
        "After creation, assign permissions via `POST /roles/{role_id}/permissions`. "
        "Then assign to users via `POST /users/{user_id}/roles`. "
        "**Requires DB migration** — see migration note in this file."
    ),
)
async def create_custom_role(
    payload:      CustomRoleCreate,
    db:           DBSession,
    current_user: Current_User,
    # _:            Current_User = _require_roles_manage,
) -> dict:
    """
    Roles allowed:  app_admin
    Permission:     roles.manage
    DB:             INSERT INTO roles (name, description, is_active, is_custom=True)
    Raises:
      400 — name clashes with system role
      409 — role name already exists
    """
    role = await service_create_custom_role(
        db          = db,
        name        = payload.name,
        description = payload.description,
        created_by  = current_user.user_id,
    )
    return {
    "id":          str(role.id),
    "name":        role.name,
    "description": role.description,
    "is_active":   role.is_active,
    "is_custom":   True,
    "created_at":  str(role.created_at),
    "updated_at":  str(role.updated_at),
}


# # =============================================================================
# # GET /roles/custom — List custom roles only
# # =============================================================================
# @custom_roles_router.get(
#     "/roles/custom",
#     status_code=status.HTTP_200_OK,
#     summary="List custom roles",
#     description="Returns only admin-created custom roles (is_custom=True). Does not include system roles.",
# )
# async def list_custom_roles(
#     db: DBSession,
#     _:  Current_User = _require_roles_manage,
# ) -> CustomRoleListResponse:
#     """
#     Roles allowed:  app_admin
#     Permission:     roles.manage
#     DB:             SELECT * FROM roles WHERE is_custom = true
#     """
#     roles = await service_list_custom_roles(db, include_all=False)
#     items = [
#         CustomRoleResponse(
#             id               = r["id"],
#             name             = r["name"],
#             description      = r.get("description"),
#             is_active        = r["is_active"],
#             is_custom        = r.get("is_custom", True),
#             permission_count = r["permission_count"],
#             user_count       = r["user_count"],
#             created_at       = r["created_at"],
#             updated_at       = r["updated_at"],
#         )
#         for r in roles
#     ]
#     return CustomRoleListResponse(items=items, total=len(items))


# # =============================================================================
# # GET /roles/all — List ALL roles (system + custom)
# # =============================================================================
# @custom_roles_router.get(
#     "/roles/all",
#     status_code=status.HTTP_200_OK,
#     summary="List all roles including system roles",
#     description=(
#         "Returns all roles — both the 4 predefined system roles "
#         "and any admin-created custom roles. "
#         "Use this for the 'Assign Role to User' dropdown."
#     ),
# )
# async def list_all_roles(
#     db: DBSession,
#     _:  Current_User = _require_roles_manage,
# ) -> CustomRoleListResponse:
#     """
#     Roles allowed:  app_admin
#     Permission:     roles.manage
#     DB:             SELECT * FROM roles ORDER BY name
#     """
#     roles = await service_list_custom_roles(db, include_all=True)
#     items = [
#         CustomRoleResponse(
#             id               = r["id"],
#             name             = r["name"],
#             description      = r.get("description"),
#             is_active        = r["is_active"],
#             is_custom        = r.get("is_custom", False),
#             permission_count = r["permission_count"],
#             user_count       = r["user_count"],
#             created_at       = r["created_at"],
#             updated_at       = r["updated_at"],
#         )
#         for r in roles
#     ]
#     return CustomRoleListResponse(items=items, total=len(items))


# # =============================================================================
# # GET /roles/custom/{role_id} — Get one custom role
# # =============================================================================
# @custom_roles_router.get(
#     "/roles/custom/{role_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Get a custom role by ID",
#     description="Returns full detail for a single role including permission and user counts.",
# )
# async def get_custom_role(
#     role_id: uuid.UUID,
#     db:      DBSession,
#     _:       Current_User = _require_roles_manage,
# ) -> CustomRoleResponse:
#     """
#     Roles allowed:  app_admin
#     Permission:     roles.manage
#     Raises:
#       404 — role not found
#     """
#     data = await service_get_custom_role(db, role_id)
#     return CustomRoleResponse(
#         id               = data["id"],
#         name             = data["name"],
#         description      = data.get("description"),
#         is_active        = data["is_active"],
#         is_custom        = data.get("is_custom", True),
#         permission_count = data["permission_count"],
#         user_count       = data["user_count"],
#         created_at       = data["created_at"],
#         updated_at       = data["updated_at"],
#     )


# # =============================================================================
# # PATCH /roles/custom/{role_id} — Update a custom role
# # =============================================================================
# @custom_roles_router.patch(
#     "/roles/custom/{role_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Update a custom role",
#     description=(
#         "Updates `description` and/or `is_active` on a role. "
#         "`name` is **immutable** after creation — changing it would break "
#         "all user_roles rows and permission checks that reference this role name."
#     ),
# )
# async def update_custom_role(
#     role_id:      uuid.UUID,
#     payload:      CustomRoleUpdate,
#     db:           DBSession,
#     current_user: Current_User,
#     _:            Current_User = _require_roles_manage,
# ) -> CustomRoleResponse:
#     """
#     Roles allowed:  app_admin
#     Permission:     roles.manage
#     Raises:
#       404 — role not found
#       400 — cannot deactivate system role with active users
#     """
#     data = await service_update_custom_role(
#         db          = db,
#         role_id     = role_id,
#         description = payload.description,
#         is_active   = payload.is_active,
#         modified_by = current_user.user_id,
#     )
#     return CustomRoleResponse(
#         id               = data["id"],
#         name             = data["name"],
#         description      = data.get("description"),
#         is_active        = data["is_active"],
#         is_custom        = data.get("is_custom", True),
#         permission_count = data["permission_count"],
#         user_count       = data["user_count"],
#         created_at       = data["created_at"],
#         updated_at       = data["updated_at"],
#     )


# # =============================================================================
# # DELETE /roles/custom/{role_id} — Delete a custom role
# # =============================================================================
# @custom_roles_router.delete(
#     "/roles/custom/{role_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Delete a custom role",
#     description=(
#         "Permanently deletes a custom role and all its permission assignments. "
#         "**Blocked** if any user currently holds this role — reassign them first. "
#         "**Blocked** for the 4 predefined system roles — they cannot be deleted."
#     ),
# )
# async def delete_custom_role(
#     role_id: uuid.UUID,
#     db:      DBSession,
#     _:       Current_User = _require_roles_manage,
# ) -> dict:
#     """
#     Roles allowed:  app_admin
#     Permission:     roles.manage
#     Raises:
#       404 — role not found
#       400 — system role (cannot delete)
#       400 — users still assigned to this role
#     """
#     return await service_delete_custom_role(db, role_id)


# # =============================================================================
# # MIGRATION GUIDE — run this before using custom roles
# # =============================================================================
# """
# STEP 1: Add is_custom column + change name to String

# Create a new Alembic migration:
#     alembic revision --autogenerate -m "custom_roles_support"

# Then edit the generated migration file to include:

#     def upgrade():
#         # Change name from enum to string
#         op.execute("ALTER TABLE roles ALTER COLUMN name TYPE VARCHAR(100)")
#         op.execute("DROP TYPE IF EXISTS user_role_name_enum")

#         # Add is_custom column
#         op.add_column('roles', sa.Column(
#             'is_custom',
#             sa.Boolean(),
#             nullable=False,
#             server_default='false'
#         ))

#     def downgrade():
#         op.drop_column('roles', 'is_custom')
#         # Re-creating the enum on downgrade is complex — handle manually


# STEP 2: Update your Role model in app/models/models.py

#     # Change this:
#     name = Column(
#         Enum("app_admin", "hr", "employee", "attorney", name="user_role_name_enum"),
#         nullable=False, unique=True
#     )

#     # To this:
#     name      = Column(String(100), nullable=False, unique=True)
#     is_custom = Column(Boolean,     default=False,  nullable=False)


# STEP 3: Run migration
#     alembic upgrade head


# STEP 4: Register the router in main.py
#     from app.api.v1.custom_roles import custom_roles_router
#     app.include_router(custom_roles_router, prefix="/api/v1", tags=["Custom Roles"])


# STEP 5: The 4 seeded roles will have is_custom=False automatically
#         (server_default='false' handles this).
#         Any new role created via POST /roles/custom will have is_custom=True.
# """
