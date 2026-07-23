from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.employee.security import (
    LoginHistoryListResponse,
    LoginSessionResponse,
    SecurityAlertPreferencesResponse,
    SecurityAlertPreferencesUpdate,
)
from app.services.employee.security_service import (
    list_login_history,
    logout_session,
    get_security_alert_preferences,
    update_security_alert_preferences,
)

employee_security_router = APIRouter()


@employee_security_router.get(
    "/security/login-history",
    response_model=LoginHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List this user's login sessions",
)
async def api_list_login_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> LoginHistoryListResponse:
    items, total = await list_login_history(
        db, current_user.user_id, limit=limit, offset=offset
    )
    return LoginHistoryListResponse(
        items=[LoginSessionResponse.model_validate(r) for r in items],
        total=total,
    )


@employee_security_router.post(
    "/security/login-history/{session_id}/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out one specific session",
    response_model=None,
)
async def api_logout_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> None:
    await logout_session(db, current_user.user_id, session_id)


@employee_security_router.get(
    "/security/security-alerts",
    response_model=SecurityAlertPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get this user's security alert Email/SMS preferences",
)
async def api_get_security_alerts(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> SecurityAlertPreferencesResponse:
    prefs = await get_security_alert_preferences(db, current_user.user_id)
    return SecurityAlertPreferencesResponse.model_validate(prefs)


@employee_security_router.patch(
    "/security/security-alerts",
    response_model=SecurityAlertPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update this user's security alert Email/SMS preferences",
)
async def api_update_security_alerts(
    updates: SecurityAlertPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> SecurityAlertPreferencesResponse:
    prefs = await update_security_alert_preferences(
        db, current_user.user_id, updates
    )
    return SecurityAlertPreferencesResponse.model_validate(prefs)