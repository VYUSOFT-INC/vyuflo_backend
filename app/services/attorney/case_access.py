# app/services/shared/case_access.py
"""
Shared case-access helper.

This was previously copy-pasted as two near-identical private functions:
  - document_request_service._is_case_staff()          → returned bool only
  - document_extra_service._is_authorized_to_upload_for_client() → same logic

Both are replaced by get_case_role() here, which returns WHICH role the
caller has on the case (not just whether they're allowed in), because the
HR-relay workflow needs to branch on that: attorney-initiated actions get
staged behind HR approval, HR-initiated (and admin) actions go straight
through.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import Application, Role, UserRole


async def get_case_role(
    db: AsyncSession,
    actor_id: uuid.UUID,
    application: Application,
) -> Optional[str]:
    """
    Returns 'app_admin' | 'attorney' | 'hr' | None.

    None means the actor has no standing on this case at all — callers
    should treat that as a 403.
    """
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == actor_id)
    )
    role_names = {r for (r,) in result.all()}

    if "app_admin" in role_names:
        return "app_admin"
    if "attorney" in role_names and application.assigned_attorney_id == actor_id:
        return "attorney"
    if "hr" in role_names and application.assigned_hr_id == actor_id:
        return "hr"
    return None


async def is_case_staff(db: AsyncSession, actor_id: uuid.UUID, application: Application) -> bool:
    """Boolean convenience wrapper for call sites that only need yes/no."""
    return await get_case_role(db, actor_id, application) is not None
