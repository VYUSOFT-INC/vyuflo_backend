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
    active_organization_id: uuid.UUID | None = None


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
        active_org    = payload.get("active_organization_id")

        if not user_id or token_type != "access":
            raise UnauthorizedException("Invalid token")

        result = await db.execute(select(User.token_version).where(User.id == uuid.UUID(user_id)))
        current_version = result.scalar_one_or_none()

        if current_version is None:
            raise UnauthorizedException("User not found")
        if current_version != token_version:
            raise UnauthorizedException("Session has been invalidated. Please log in again.")

        active_organization_id = None
        if active_org:
            try:
                active_organization_id = uuid.UUID(str(active_org))
            except (ValueError, TypeError):
                active_organization_id = None

        return CurrentUserData(
            user_id=uuid.UUID(user_id),
            roles=roles,
            email=payload.get("email"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            active_organization_id=active_organization_id,
        )

    except (JWTError, ValueError, KeyError):
        raise UnauthorizedException("Could not validate credentials")


Current_User = Annotated[CurrentUserData, Depends(get_current_user)]
DBSession     = Annotated[AsyncSession, Depends(get_db)]
