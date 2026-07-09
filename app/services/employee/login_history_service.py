# src/app/services/login_history_service.py
from __future__ import annotations
import uuid
from typing import Optional
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.visamodels import UserLoginHistory
from app.schemas.employee.login_history import (
    LoginHistoryResponse,
    LoginHistoryListResponse,
    LoginHistoryMarkSuspicious,
)
from app.services.employee.services import db_update, db_get_by_id


async def list_login_history(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    limit:           int = 20,
    offset:          int = 0,
) -> LoginHistoryListResponse:
    """
    GET /users/me/login-history
    Returns paginated login history for the current user, newest first.
    """
    # Items
    stmt = (
        select(UserLoginHistory)
        .where(UserLoginHistory.user_id == current_user_id)
        .order_by(UserLoginHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    # Total count
    count_stmt = (
        select(func.count())
        .select_from(UserLoginHistory)
        .where(UserLoginHistory.user_id == current_user_id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    return LoginHistoryListResponse(
        items=[LoginHistoryResponse.model_validate(i) for i in items],
        total=total,
    )


async def mark_suspicious(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    history_id:      uuid.UUID,
) -> LoginHistoryResponse:
    """
    PATCH /users/me/login-history/:id/suspicious
    User clicked "Report" on a suspicious login entry.
    """
    entry = await db_get_by_id(db, UserLoginHistory, history_id)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Login history entry not found.",
        )
    if entry.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this entry.",
        )

    updated = await db_update(
        db,
        UserLoginHistory,
        history_id,
        {
            "is_suspicious": True,
            "modified_by":   current_user_id,
        },
    )
    return LoginHistoryResponse.model_validate(updated)


async def sign_out_all_devices(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
) -> dict:
    """
    POST /users/me/sign-out-all
    Marks all active sessions as logged out except the current session.
    """
    stmt = (
        select(UserLoginHistory)
        .where(
            UserLoginHistory.user_id          == current_user_id,
            UserLoginHistory.logged_out_at    == None,        # noqa: E711
            UserLoginHistory.is_current_session == False,     # noqa: E712
        )
    )
    result = await db.execute(stmt)
    active_sessions = result.scalars().all()

    now = datetime.now(timezone.utc)
    for session in active_sessions:
        await db_update(
            db,
            UserLoginHistory,
            session.id,
            {
                "logged_out_at": now,
                "modified_by":   current_user_id,
            },
        )

    return {
        "detail":        "Signed out from all devices successfully.",
        "sessions_ended": len(active_sessions),
    }