from __future__ import annotations
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import UserLoginHistory, NotificationPreferences
from app.schemas.employee.security import SecurityAlertPreferencesUpdate


# =============================================================================
# LOGIN HISTORY
# =============================================================================

async def list_login_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[UserLoginHistory], int]:
    """
    GET /security/login-history
    Returns this user's login sessions, most recent first.
    """
    stmt = (
        select(UserLoginHistory)
        .where(UserLoginHistory.user_id == user_id)
        .order_by(UserLoginHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    count_stmt = (
        select(func.count())
        .select_from(UserLoginHistory)
        .where(UserLoginHistory.user_id == user_id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    return list(rows), total


async def logout_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> None:
    """
    POST /security/login-history/{session_id}/logout
    Ends one specific session (the "Logout" button in screenshot 3).
    Raises 404 if it doesn't exist or doesn't belong to this user —
    this stops user A from logging out user B's session by guessing an id.
    """
    stmt = select(UserLoginHistory).where(
        UserLoginHistory.id == session_id,
        UserLoginHistory.user_id == user_id,
    )
    result = await db.execute(stmt)
    session_row = result.scalar_one_or_none()

    if not session_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Login session {session_id} not found.",
        )

    session_row.logged_out_at = datetime.now(timezone.utc)
    session_row.is_current_session = False
    await db.flush()


# =============================================================================
# SECURITY ALERT PREFERENCES
# =============================================================================

async def get_security_alert_preferences(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> NotificationPreferences:
    """
    GET /security/security-alerts
    Returns the user's preferences row.

    Users who signed up before this feature existed won't have a row yet —
    in that case we create one on the fly using the column defaults, so the
    endpoint never 404s and the frontend always gets something to render.
    """
    stmt = select(NotificationPreferences).where(
        NotificationPreferences.user_id == user_id
    )
    result = await db.execute(stmt)
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = NotificationPreferences(user_id=user_id)
        db.add(prefs)
        await db.flush()

    return prefs


async def update_security_alert_preferences(
    db: AsyncSession,
    user_id: uuid.UUID,
    updates: SecurityAlertPreferencesUpdate,
) -> NotificationPreferences:
    """
    PATCH /security/security-alerts
    Applies only the checkbox(es) the client actually sent — anything
    left out of the request body is left untouched.
    """
    prefs = await get_security_alert_preferences(db, user_id)

    changes = updates.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(prefs, field, value)

    await db.flush()
    return prefs
