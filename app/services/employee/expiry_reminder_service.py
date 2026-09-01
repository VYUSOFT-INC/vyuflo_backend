"""
expiry_reminder_service.py
===========================
Daily check: find documents whose expiry_date falls within a reminder
threshold, and notify the owning employee via fire_document_expiring().
Idempotent — DocumentExpiryReminder rows prevent double-sends.

Thresholds are admin-configurable via SystemSetting (documents.expiry_reminder_thresholds).
No hardcoded fallback — the seed data guarantees this row always exists.

FIXED (both functions below): neither query excluded documents already
marked "superseded". Once someone replaces a document early (before it
actually expires — see reupload_expired_document()), the OLD row keeps its
original expiry_date, so without this exclusion the scheduler kept sending
"expires in N days" reminders and would eventually flip that historical,
no-longer-relevant document to "expired" and fire a "please re-upload"
notification for something nobody uses anymore.

FIXED (threshold matching): was sorting thresholds descending and taking
the first match, so a document with 1 day left would always match the
LARGEST threshold (e.g. 90) instead of the tightest one — the 60/30/14/7/1
day reminders could never fire correctly. Now sorts ascending and picks the
smallest threshold that's still >= days_remaining.

REMOVED: automatic "Renew {document type}" task creation on reminder.
This was tried and reverted — it created documents through a separate
upload path (plain upload_document(), keyed off the task's own name as a
free-text document_type) instead of through reupload_expired_document(),
which is the ONLY path that correctly chains the new document to the old
one via parent_document_id. In practice this meant a renewal-task upload
produced an orphaned, unrelated document under a brand-new auto-created
DocumentType ("Renew Passport Copy") with no version chain at all, while
the existing "Replace" button on the original (already-completed) task
worked correctly the whole time. Rather than fix two divergent paths to
the same document, we're keeping exactly one: Replace. The
document-level versioning (parent_document_id / superseded / activates_on)
remains the single source of truth for "what changed and when" — no
separate task duplication needed.

Reminders still fire exactly as before; they just no longer spawn an
extra pending task alongside the notification. The notification's CTA
still routes to the case's tasks tab (or the Hub), where the person finds
the same already-completed task with a Replace button on it.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.visamodels import Document, DocumentExpiryReminder, SystemSetting
from app.services.employee.notification_service import (
    _create_notification,
    dispatch_notification,
    fire_document_expiring,
)
from app.services.employee.services import db_create, db_update

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
        select(Document).where(
            Document.expiry_date.is_not(None),
            # a superseded document's expiry_date is stale — it's been
            # replaced, so it should never generate a reminder.
            Document.status != "superseded",
        )
    )
    documents: Sequence[Document] = result.scalars().all()

    for doc in documents:
        days_remaining = (doc.expiry_date - today).days
        if days_remaining < 0:
            continue

        matching_threshold = None
        # Sort ascending — pick the SMALLEST threshold that's still >=
        # days_remaining, i.e. the tightest, most urgent bucket that
        # currently applies. (Descending + first-match would always land
        # on the largest threshold instead — the bug this replaced.)
        for threshold in sorted(reminder_thresholds):
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


async def activate_pending_document_replacements(db: AsyncSession) -> int:
    """
    Daily job — performs the actual old-to-new handoff for documents that
    were replaced BEFORE their predecessor expired (see
    reupload_expired_document()'s old_still_valid branch).

    Those new documents were created with activates_on = old_doc.expiry_date
    and the OLD document was deliberately left untouched (still "verified"
    etc.) at replace time, because it was still the person's legitimate,
    currently-valid document. This job is what finally marks the old one
    "superseded" — but only once its actual expiry date has arrived, never
    before.

    Idempotent — only touches documents whose activates_on has arrived and
    is still set (cleared to None once processed), so re-running this on
    every scheduler tick is safe.
    """
    today = date.today()

    result = await db.execute(
        select(Document).where(
            Document.activates_on.is_not(None),
            Document.activates_on <= today,
        )
    )
    ready_docs = result.scalars().all()

    activated = 0
    for new_doc in ready_docs:
        if not new_doc.parent_document_id:
            await db_update(db, Document, new_doc.id, {"activates_on": None})
            continue

        old_doc = await db.get(Document, new_doc.parent_document_id)
        if old_doc and old_doc.status != "superseded":
            await db_update(db, Document, old_doc.id, {"status": "superseded"})

        await db_update(db, Document, new_doc.id, {"activates_on": None})
        activated += 1

    await db.commit()
    return activated


async def mark_expired_documents(db: AsyncSession) -> int:
    """
    Flip any document whose expiry_date has passed to status='expired'
    and fire a one-time 'document_expired' notification. Idempotent —
    only touches documents not already marked expired, so safe to run
    on every scheduler tick.

    Deliberately does NOT touch ApplicationTask.is_completed — a task that
    was genuinely completed at filing time stays completed for historical
    accuracy. Only a person deliberately replacing the document (via
    reupload_expired_document()) resets that.
    """
    today = datetime.now(timezone.utc).date()

    result = await db.execute(
        select(Document).where(
            Document.expiry_date.isnot(None),
            Document.expiry_date < today,
            Document.status != "expired",
            Document.status != "superseded",
        )
    )
    docs = result.scalars().all()

    for doc in docs:
        await db_update(db, Document, doc.id, {"status": "expired"})

        cta_url = (
            f"/applications/{doc.application_id}?tab=tasks"
            if doc.application_id
            else f"/documents?reupload={doc.id}"
        )

        notif = await _create_notification(
            db,
            user_id=doc.user_id,
            notification_type="document_expired",
            category="document",
            priority="high",
            title="A document has expired",
            body=f"{doc.file_name} has expired and needs to be re-uploaded.",
            document_id=doc.id,
            application_id=doc.application_id,
            cta_primary_label="Re-upload",
            cta_primary_url=cta_url
        )

        await dispatch_notification(
            db,
            notif_id=notif.id,
            user_id=doc.user_id,
            subject=f"VyuFlo — {doc.file_name} has expired",
            body_text=(
                f"Hi,\n\nYour document \"{doc.file_name}\" has expired and needs "
                f"to be re-uploaded.\n\n"
                f"Take care of it at: {settings.FRONTEND_URL}{cta_url}\n\nVyuFlo Team"
            ),
            category_pref_field="notify_document_updates",
            cta_label="Re-upload",
            cta_url=cta_url,
            event_key="document_expired",
            template_context={
                "document_name": doc.file_name,
                "action_url":    f"{settings.FRONTEND_URL}{cta_url}",
            },
        )

    await db.commit()
    return len(docs)