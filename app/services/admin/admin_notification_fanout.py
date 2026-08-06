"""
app/services/admin/admin_notification_fanout.py

"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import Notification, Role, User, UserRole


async def fan_out_notification_to_admins(
    db: AsyncSession,
    source: Notification,
) -> None:
    """
    Given a Notification row that was just created for its primary
    recipient (source.user_id), inserts a copy for every active admin user.
    """
    admin_rows = await db.execute(
        select(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.name == "app_admin", User.is_active == True)  # noqa: E712
    )
    admin_ids = [row[0] for row in admin_rows.all()]

    for admin_id in admin_ids:
        if admin_id == source.user_id:
            continue

        db.add(Notification(
            id=uuid.uuid4(),
            user_id=admin_id,
            notification_type=source.notification_type,
            category=source.category,
            priority=source.priority,
            title=source.title,
            body=source.body,
            application_id=source.application_id,
            document_id=source.document_id,
            case_reference=source.case_reference,
            actor_id=source.user_id,
            actor_label=source.actor_label,
            cta_primary_label=source.cta_primary_label,
            cta_primary_url=source.cta_primary_url,
            cta_secondary_label=source.cta_secondary_label,
            cta_secondary_url=source.cta_secondary_url,
        ))

    if admin_ids:
        await db.flush()