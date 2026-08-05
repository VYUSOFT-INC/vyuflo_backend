"""
expiry_reminder_service.py
===========================
Daily check: find documents whose expiry_date falls within a reminder
threshold, and notify the owning employee via fire_document_expiring().
Idempotent — DocumentExpiryReminder rows prevent double-sends.

Thresholds are admin-configurable via SystemSetting (documents.expiry_reminder_thresholds).
No hardcoded fallback — the seed data guarantees this row always exists.
"""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import Document, DocumentExpiryReminder, SystemSetting
from app.services.employee.notification_service import fire_document_expiring
from app.services.employee.services import db_create

SETTING_KEY = "documents.expiry_reminder_thresholds"


async def _get_reminder_thresholds(db: AsyncSession) -> tuple[int, ...]:
    """
    Reads admin-configured thresholds from SystemSetting, comma-separated
    (e.g. "90,60,30,14,7,1"). Raises if missing/malformed — the seed
    guarantees this row exists, so a missing row means the seed itself
    failed, which should be surfaced loudly.
    """
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == SETTING_KEY).limit(1)
    )
    setting = result.scalars().first()

    if not setting or not setting.value:
        raise ValueError(
            f"SystemSetting '{SETTING_KEY}' is missing — check that "
            f"seed_system_settings() ran and includes this key."
        )

    parsed = tuple(
        int(x.strip()) for x in setting.value.split(",") if x.strip().isdigit()
    )
    if not parsed:
        raise ValueError(
            f"SystemSetting '{SETTING_KEY}' has an unparseable value: {setting.value!r}"
        )

    return parsed


async def _already_sent(db: AsyncSession, document_id, threshold_days: int) -> bool:
    result = await db.execute(
        select(DocumentExpiryReminder).where(
            and_(
                DocumentExpiryReminder.document_id == document_id,
                DocumentExpiryReminder.threshold_days == threshold_days,
            )
        ).limit(1)
    )
    return result.scalars().first() is not None


async def check_and_send_expiry_reminders(db: AsyncSession) -> int:
    today = date.today()
    sent_count = 0

    reminder_thresholds = await _get_reminder_thresholds(db)

    result = await db.execute(
        select(Document).where(Document.expiry_date.is_not(None))
    )
    documents: Sequence[Document] = result.scalars().all()

    for doc in documents:
        days_remaining = (doc.expiry_date - today).days
        if days_remaining < 0:
            continue

        matching_threshold = None
        for threshold in sorted(reminder_thresholds, reverse=True):
            if days_remaining <= threshold:
                matching_threshold = threshold
                break
        if matching_threshold is None:
            continue

        if await _already_sent(db, doc.id, matching_threshold):
            continue

        await fire_document_expiring(
            db,
            user_id=doc.user_id,
            document_id=doc.id,
            document_name=doc.file_name,
            expiry_date_str=doc.expiry_date.strftime("%b %d, %Y"),
            days_remaining=days_remaining,
            application_id=doc.application_id,
        )

        await db_create(db, DocumentExpiryReminder(
            document_id=doc.id,
            threshold_days=matching_threshold,
        ))
        sent_count += 1

    await db.commit()
    return sent_count