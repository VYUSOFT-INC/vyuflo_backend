# src/app/routers/login_history_router.py
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.employee.login_history import LoginHistoryListResponse, LoginHistoryResponse
from app.services.employee.login_history_service import (
    list_login_history,
    mark_suspicious,
    sign_out_all_devices,
)

login_history_router = APIRouter()


@login_history_router.get(
    "/users/me/login-history",
    response_model=LoginHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get login history",
    description="Returns paginated login history for the current user, newest first.",
)
async def api_list_login_history(
    limit:           int        = Query(20, ge=1, le=100),
    offset:          int        = Query(0, ge=0),
    db:              AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID  = Depends(get_current_user),
) -> LoginHistoryListResponse:
    return await list_login_history(db, current_user_id.user_id, limit, offset)


@login_history_router.patch(
    "/users/me/login-history/{history_id}/suspicious",
    response_model=LoginHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark login as suspicious",
    description="User reports a login entry as suspicious. Sets is_suspicious = True.",
)
async def api_mark_suspicious(
    history_id:      uuid.UUID,
    db:              AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID   = Depends(get_current_user),
) -> LoginHistoryResponse:
    return await mark_suspicious(db, current_user_id.user_id, history_id)


@login_history_router.post(
    "/users/me/sign-out-all",
    status_code=status.HTTP_200_OK,
    summary="Sign out all devices",
    description="Logs out all active sessions except the current one.",
)
async def api_sign_out_all(
    db:              AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID   = Depends(get_current_user),
) -> dict:
    return await sign_out_all_devices(db, current_user_id.user_id)