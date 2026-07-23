# """
# Reusable FastAPI dependency injectors.
# """
# from typing import Annotated, Optional
# import uuid

# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from jose import JWTError
# from pydantic import BaseModel
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.database import get_db
# from app.core.security import decode_token
# from app.core.exceptions import UnauthorizedException

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# class CurrentUserData(BaseModel):
#     user_id: uuid.UUID
#     roles: list[str]

# async def get_current_user(
#     token: Annotated[str, Depends(oauth2_scheme)],
# ) -> CurrentUserData:
#     try:
#         payload = decode_token(token)

#         user_id = payload.get("sub")   
#         roles = payload.get("roles", [])  
#         token_type = payload.get("type")

#         if not user_id or token_type != "access":
#             raise UnauthorizedException("Invalid token")

#         return CurrentUserData(
#             user_id=uuid.UUID(user_id),
#             roles=roles
#         )

#     except (JWTError, ValueError, KeyError):
#         raise UnauthorizedException("Could not validate credentials")

    
# # ── Typed aliases for route signatures ───────────────────────────────────────
# Current_User = Annotated[CurrentUserData, Depends(get_current_user)]
# DBSession     = Annotated[AsyncSession, Depends(get_db)]

# from functools import lru_cache
# from typing import Callable

# # Maps permission codes → which roles are allowed
# # Mirrors ROLE_PERMISSIONS_SEED exactly
# _PERMISSION_ROLE_MAP: dict[str, set[str]] = {
#     # Time Entries
#     "time_entries:read":        {"attorney", "app_admin"},
#     "time_entries:create":      {"attorney", "app_admin"},
#     "time_entries:update":      {"attorney", "app_admin"},
#     "time_entries:delete":      {"attorney", "app_admin"},
#     "time_entries:bulk_action": {"attorney", "app_admin"},
#     # Invoices
#     "invoices:read":            {"attorney", "app_admin"},
#     "invoices:create":          {"attorney", "app_admin"},
#     "invoices:update":          {"attorney", "app_admin"},
#     "invoices:send":            {"attorney", "app_admin"},
#     "invoices:void":            {"app_admin"},
#     # Billing Clients
#     "billing_clients:read":     {"attorney", "app_admin"},
#     "billing_clients:manage":   {"app_admin"},
#     # Dashboard
#     "billing:dashboard":        {"attorney", "app_admin"},
#     "billing:reports":          {"app_admin"},
# }


# def require_permission(permission_code: str) -> Callable:
#     """
#     FastAPI dependency factory.
#     Checks if any of the user's JWT roles are allowed for this permission.

#     Usage:
#         _perm: None = Depends(require_permission("billing:dashboard"))
#     """
#     def _check(current_user: CurrentUserData = Depends(get_current_user)) -> None:
#         allowed_roles = _PERMISSION_ROLE_MAP.get(permission_code, set())
#         user_roles    = set(current_user.roles)

#         if not user_roles.intersection(allowed_roles):
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail=f"Permission denied. Required permission: '{permission_code}'",
#             )
#     return _check
"""
Reusable FastAPI dependency injectors.
"""
from typing import Annotated
import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException
from app.models.visamodels import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class CurrentUserData(BaseModel):
    user_id: uuid.UUID
    roles: list[str]
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUserData:
    try:
        payload = decode_token(token)

        user_id       = payload.get("sub")
        roles         = payload.get("roles", [])
        token_type    = payload.get("type")
        token_version = payload.get("token_version", 0)

        if not user_id or token_type != "access":
            raise UnauthorizedException("Invalid token")

        # ── Instant revocation check ────────────────────────────────────────
        # If the DB's token_version is higher than what's in this token, the
        # token was issued before a security event (password change, forced
        # logout, role change) — reject immediately, even if not yet expired.
        result = await db.execute(select(User.token_version).where(User.id == uuid.UUID(user_id)))
        current_version = result.scalar_one_or_none()

        if current_version is None:
            raise UnauthorizedException("User not found")
        if current_version != token_version:
            raise UnauthorizedException("Session has been invalidated. Please log in again.")

        return CurrentUserData(
            user_id=uuid.UUID(user_id),
            roles=roles,
            email=payload.get("email"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
        )

    except (JWTError, ValueError, KeyError):
        raise UnauthorizedException("Could not validate credentials")


# ── Typed aliases for route signatures ───────────────────────────────────────
Current_User = Annotated[CurrentUserData, Depends(get_current_user)]
DBSession     = Annotated[AsyncSession, Depends(get_db)]