from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_email
from app.models.visamodels import (
    Application,
    Deadline,
    Notification,
    NotificationPreferences,
    User,
)
from app.schemas.employee.notification_schemas import (
    MarkReadResponse,
    NotificationListResponse,
    NotificationOut,
    NotificationPreferencesOut,
    NotificationStatsResponse,
    UpdatePreferencesRequest,
)

logger = logging.getLogger(__name__)


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_or_create_prefs(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> NotificationPreferences:
    result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.user_id == user_id
        )
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        prefs = NotificationPreferences(user_id=user_id)
        db.add(prefs)
        await db.flush()
    return prefs


async def _get_user(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def _render(template: str, context: dict[str, str]) -> str:
    for key, value in context.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template


async def _create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_type: str,
    category: str,
    priority: str,
    title: str,
    body: str,
    application_id: Optional[uuid.UUID] = None,
    document_id: Optional[uuid.UUID] = None,
    case_reference: Optional[str] = None,
    actor_id: Optional[uuid.UUID] = None,
    actor_label: Optional[str] = None,
    cta_primary_label: Optional[str] = None,
    cta_primary_url: Optional[str] = None,
    cta_secondary_label: Optional[str] = None,
    cta_secondary_url: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        notification_type=notification_type,
        category=category,
        priority=priority,
        title=title,
        body=body,
        application_id=application_id,
        document_id=document_id,
        case_reference=case_reference,
        actor_id=actor_id,
        actor_label=actor_label,
        cta_primary_label=cta_primary_label,
        cta_primary_url=cta_primary_url,
        cta_secondary_label=cta_secondary_label,
        cta_secondary_url=cta_secondary_url,
        expires_at=expires_at,
    )
    db.add(notif)
    await db.flush()
    return notif


async def _maybe_send_email(
    db: AsyncSession,
    notif_id: uuid.UUID,          # ← plain UUID, not the ORM object
    user_id: uuid.UUID,
    subject: str,
    body_text: str,
    category_pref_field: str,
) -> None:
    """
    FIX 1: Accept notif_id (UUID) instead of the ORM Notification object.
            After db.commit() in the parent, ORM objects are expired and
            accessing their attributes triggers a sync lazy-load which fails
            with MissingGreenlet in async context.

    FIX 2: await db.rollback() on failure so the session isn't left poisoned
            for subsequent DB calls in the same request.

    FIX 3: notify_compliance_alerts column — if _get_or_create_prefs() fails
            because a column doesn't exist yet, the rollback here prevents the
            session poisoning that would otherwise cascade into notification
            inserts for subsequent recipients.
    """
    try:
        prefs = await _get_or_create_prefs(db, user_id)
        if not prefs.email_enabled:
            return
        if not getattr(prefs, category_pref_field, True):
            return

        user = await _get_user(db, user_id)
        if not user or not user.email:
            return

        await send_email(to=user.email, subject=subject, body=body_text)

        # Re-fetch the notification by ID to avoid using an expired ORM object
        result = await db.execute(
            select(Notification).where(Notification.id == notif_id)
        )
        notif = result.scalar_one_or_none()
        if notif:
            notif.sent_via_email = True
            await db.flush()

    except Exception:
        logger.exception("Failed to send email for notification %s", notif_id)
        await db.rollback()


# =============================================================================
# READ-SIDE  (called by routes)
# =============================================================================

async def list_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    category: Optional[str] = None,
    is_read: Optional[bool] = None,
    priority: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> NotificationListResponse:
    base = (
        select(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_dismissed == False,  # noqa: E712
        )
        .order_by(Notification.created_at.desc())
    )

    if category:
        base = base.where(Notification.category == category)
    if is_read is not None:
        base = base.where(Notification.is_read == is_read)
    if priority:
        base = base.where(Notification.priority == priority)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows = (
        await db.execute(base.limit(limit).offset(offset))
    ).scalars().all()

    stats = await _raw_stats(db, user_id)

    return NotificationListResponse(
        items=[NotificationOut.model_validate(n) for n in rows],
        total=total,
        unread_count=stats["unread_count"],
        urgent_count=stats["urgent_count"],
        has_more=(offset + limit) < total,
    )


async def _raw_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    from datetime import timedelta

    now = _now()
    week_ago = now - timedelta(days=7)

    unread = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
                Notification.is_dismissed == False,  # noqa: E712
            )
        )
    ).scalar_one()

    urgent = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.priority == "urgent",
                Notification.is_read == False,  # noqa: E712
                Notification.is_dismissed == False,  # noqa: E712
            )
        )
    ).scalar_one()

    week = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.created_at >= week_ago,
                Notification.is_dismissed == False,  # noqa: E712
            )
        )
    ).scalar_one()

    news = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.category == "news",
                Notification.is_dismissed == False,  # noqa: E712
            )
        )
    ).scalar_one()

    return {
        "unread_count": unread,
        "urgent_count": urgent,
        "week_count": week,
        "news_count": news,
    }


async def get_notification_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> NotificationStatsResponse:
    stats = await _raw_stats(db, user_id)
    return NotificationStatsResponse(**stats)


# =============================================================================
# MARK READ / DISMISS
# =============================================================================

async def mark_notification_read(
    db: AsyncSession,
    user_id: uuid.UUID,
    notif_id: uuid.UUID,
) -> MarkReadResponse:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return MarkReadResponse(updated=0, message="Notification not found.")

    if not notif.is_read:
        notif.is_read = True
        notif.read_at = _now()
        await db.flush()

    return MarkReadResponse(updated=1, message="Marked as read.")


async def mark_all_read(
    db: AsyncSession,
    user_id: uuid.UUID,
    category: Optional[str] = None,
) -> MarkReadResponse:
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
            Notification.is_dismissed == False,  # noqa: E712
        )
        .values(is_read=True, read_at=_now())
    )
    if category:
        stmt = stmt.where(Notification.category == category)

    result = await db.execute(stmt)
    count = result.rowcount
    return MarkReadResponse(updated=count, message=f"{count} notification(s) marked as read.")


async def dismiss_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    notif_id: uuid.UUID,
) -> MarkReadResponse:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return MarkReadResponse(updated=0, message="Notification not found.")

    notif.is_dismissed = True
    notif.dismissed_at = _now()
    if not notif.is_read:
        notif.is_read = True
        notif.read_at = _now()
    await db.flush()

    return MarkReadResponse(updated=1, message="Notification dismissed.")


# =============================================================================
# PREFERENCES
# =============================================================================

async def get_preferences(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> NotificationPreferencesOut:
    prefs = await _get_or_create_prefs(db, user_id)
    await db.commit()
    return NotificationPreferencesOut.model_validate(prefs)


async def update_preferences(
    db: AsyncSession,
    user_id: uuid.UUID,
    body: UpdatePreferencesRequest,
) -> NotificationPreferencesOut:
    prefs = await _get_or_create_prefs(db, user_id)

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    await db.flush()
    return NotificationPreferencesOut.model_validate(prefs)


# =============================================================================
# EVENT TRIGGERS
# =============================================================================

async def fire_case_created(
    db: AsyncSession,
    application: Application,
    *,
    actor_id: uuid.UUID,
) -> None:
    # Cache plain values immediately — never access ORM attributes inside
    # except blocks or after a parent commit(), since expired attributes
    # trigger sync lazy-loads which fail with MissingGreenlet in async context.
    app_id  = application.id
    app_num = application.application_number
    user_id = application.user_id
    hr_id   = application.assigned_hr_id
    att_id  = application.assigned_attorney_id

    try:
        actor = await _get_user(db, actor_id)
        actor_label = f"{actor.first_name} {actor.last_name}" if actor else "System"
        case_ref = app_num
        app_url  = f"/applications/{app_id}"

        emp_notif = await _create_notification(
            db,
            user_id=user_id,
            notification_type="case_status_updated",
            category="case_update",
            priority="high",
            title="Your visa application has been created",
            body=(
                f"Application {case_ref} has been successfully created. "
                "Your attorney will review and begin processing soon."
            ),
            application_id=app_id,
            case_reference=case_ref,
            actor_id=actor_id,
            actor_label=actor_label,
            cta_primary_label="View Application",
            cta_primary_url=app_url,
        )
        await _maybe_send_email(
            db, emp_notif.id, user_id,
            subject=f"VisaFlow — Application {case_ref} Created",
            body_text=(
                f"Hi,\n\nYour visa application {case_ref} has been created.\n"
                f"Track your progress: {app_url}\n\nVisaFlow Team"
            ),
            category_pref_field="notify_case_updates",
        )

        if hr_id:
            hr_notif = await _create_notification(
                db,
                user_id=hr_id,
                notification_type="case_status_updated",
                category="case_update",
                priority="high",
                title=f"New case assigned — {case_ref}",
                body=(
                    f"A new visa application ({case_ref}) has been created "
                    "and assigned to you for review."
                ),
                application_id=app_id,
                case_reference=case_ref,
                actor_id=actor_id,
                actor_label=actor_label,
                cta_primary_label="Review Case",
                cta_primary_url=app_url,
            )
            await _maybe_send_email(
                db, hr_notif.id, hr_id,
                subject=f"VisaFlow — New Case Assigned: {case_ref}",
                body_text=(
                    f"A new application ({case_ref}) has been assigned to you.\n"
                    f"Review it: {app_url}\n\nVisaFlow Team"
                ),
                category_pref_field="notify_case_updates",
            )

        if att_id:
            att_notif = await _create_notification(
                db,
                user_id=att_id,
                notification_type="case_status_updated",
                category="case_update",
                priority="high",
                title=f"New case assigned — {case_ref}",
                body=(
                    f"Case {case_ref} has been assigned to you. "
                    "Please review and begin the eligibility assessment."
                ),
                application_id=app_id,
                case_reference=case_ref,
                actor_id=actor_id,
                actor_label=actor_label,
                cta_primary_label="Open Case",
                cta_primary_url=app_url,
            )
            await _maybe_send_email(
                db, att_notif.id, att_id,
                subject=f"VisaFlow — New Case Assigned: {case_ref}",
                body_text=(
                    f"Case {case_ref} has been assigned to you.\n"
                    f"Open it here: {app_url}\n\nVisaFlow Team"
                ),
                category_pref_field="notify_case_updates",
            )

    except Exception:
        logger.exception("fire_case_created failed for application %s", app_id)
        await db.rollback()


async def fire_case_assigned_to_hr(
    db: AsyncSession,
    application: Application,
    *,
    new_hr_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    app_id  = application.id
    app_num = application.application_number
    user_id = application.user_id

    try:
        actor = await _get_user(db, actor_id)
        actor_label = f"{actor.first_name} {actor.last_name}" if actor else "System"
        hr_user = await _get_user(db, new_hr_id)
        hr_name = f"{hr_user.first_name} {hr_user.last_name}" if hr_user else "HR"
        case_ref = app_num
        app_url  = f"/applications/{app_id}"

        hr_notif = await _create_notification(
            db,
            user_id=new_hr_id,
            notification_type="participant_added",
            category="case_update",
            priority="high",
            title=f"You have been assigned to case {case_ref}",
            body=(
                f"{actor_label} has assigned case {case_ref} to you. "
                "Please review the case details and take necessary action."
            ),
            application_id=app_id,
            case_reference=case_ref,
            actor_id=actor_id,
            actor_label=actor_label,
            cta_primary_label="Open Case",
            cta_primary_url=app_url,
        )
        await _maybe_send_email(
            db, hr_notif.id, new_hr_id,
            subject=f"VisaFlow — Case {case_ref} Assigned to You",
            body_text=(
                f"Hi {hr_name},\n\n"
                f"Case {case_ref} has been assigned to you by {actor_label}.\n"
                f"Open it: {app_url}\n\nVisaFlow Team"
            ),
            category_pref_field="notify_case_updates",
        )

        emp_notif = await _create_notification(
            db,
            user_id=user_id,
            notification_type="participant_added",
            category="case_update",
            priority="medium",
            title="HR contact assigned to your case",
            body=f"{hr_name} has been assigned as your HR contact for case {case_ref}.",
            application_id=app_id,
            case_reference=case_ref,
            actor_id=actor_id,
            actor_label=actor_label,
            cta_primary_label="View Case",
            cta_primary_url=app_url,
        )
        await _maybe_send_email(
            db, emp_notif.id, user_id,
            subject=f"VisaFlow — HR Assigned to Your Case {case_ref}",
            body_text=(
                f"Hi,\n\n{hr_name} has been assigned to your case {case_ref}.\n"
                f"View your application: {app_url}\n\nVisaFlow Team"
            ),
            category_pref_field="notify_case_updates",
        )

    except Exception:
        logger.exception("fire_case_assigned_to_hr failed for application %s", app_id)
        await db.rollback()


async def fire_case_status_changed(
    db: AsyncSession,
    application: Application,
    *,
    old_status: str,
    new_status: str,
    actor_id: uuid.UUID,
    note: Optional[str] = None,
) -> None:
    app_id  = application.id
    app_num = application.application_number
    user_id = application.user_id
    hr_id   = application.assigned_hr_id
    att_id  = application.assigned_attorney_id

    try:
        actor = await _get_user(db, actor_id)
        actor_label = f"{actor.first_name} {actor.last_name}" if actor else "System"
        case_ref = app_num
        app_url  = f"/applications/{app_id}"

        priority_map = {
            "action_needed": "urgent",
            "rfe_response":  "urgent",
            "rejected":      "high",
            "approved":      "high",
            "submitted":     "medium",
            "in_progress":   "medium",
        }
        priority = priority_map.get(new_status, "low")

        status_labels = {
            "draft":         "Draft",
            "in_progress":   "In Progress",
            "action_needed": "Action Needed",
            "rfe_response":  "RFE Response Required",
            "submitted":     "Submitted",
            "approved":      "Approved ✓",
            "rejected":      "Rejected",
            "withdrawn":     "Withdrawn",
        }
        new_label = status_labels.get(new_status, new_status.replace("_", " ").title())

        body = f"Your case {case_ref} status has been updated to: {new_label}."
        if note:
            body += f"\n\nNote: {note}"

        recipients: list[tuple[uuid.UUID, str]] = [(user_id, "employee")]
        if hr_id:
            recipients.append((hr_id, "hr"))
        if att_id:
            recipients.append((att_id, "attorney"))

        for recipient_id, role in recipients:
            title = (
                f"Case update — {new_label}"
                if role == "employee"
                else f"Case {case_ref} status changed to {new_label}"
            )
            notif = await _create_notification(
                db,
                user_id=recipient_id,
                notification_type="case_status_updated",
                category="case_update",
                priority=priority,
                title=title,
                body=body,
                application_id=app_id,
                case_reference=case_ref,
                actor_id=actor_id,
                actor_label=actor_label,
                cta_primary_label="View Case",
                cta_primary_url=app_url,
            )
            await _maybe_send_email(
                db, notif.id, recipient_id,
                subject=f"VisaFlow — Case {case_ref}: {new_label}",
                body_text=(
                    f"Hi,\n\nCase {case_ref} has been updated.\n"
                    f"New status: {new_label}\n"
                    f"{('Note: ' + note) if note else ''}\n\n"
                    f"View it here: {app_url}\n\nVisaFlow Team"
                ),
                category_pref_field="notify_case_updates",
            )

    except Exception:
        logger.exception("fire_case_status_changed failed for application %s", app_id)
        await db.rollback()


async def fire_hr_approval_changed(
    db: AsyncSession,
    application: Application,
    *,
    new_approval_status: str,
    actor_id: uuid.UUID,
    hr_notes: Optional[str] = None,
) -> None:
    app_id  = application.id
    app_num = application.application_number
    user_id = application.user_id

    try:
        actor = await _get_user(db, actor_id)
        actor_label = f"{actor.first_name} {actor.last_name}" if actor else "HR"
        case_ref = app_num
        app_url  = f"/applications/{app_id}"

        messages = {
            "approved":          ("Your case has been approved by HR", "high"),
            "rejected":          ("Your case has been rejected by HR", "urgent"),
            "changes_requested": ("HR has requested changes to your case", "urgent"),
        }
        title, priority = messages.get(
            new_approval_status,
            (f"HR review update on {case_ref}", "medium"),
        )

        body = f"{actor_label} has updated the HR review status for case {case_ref}."
        if hr_notes:
            body += f"\n\nHR Notes: {hr_notes}"

        notif = await _create_notification(
            db,
            user_id=user_id,
            notification_type="case_status_updated",
            category="case_update",
            priority=priority,
            title=title,
            body=body,
            application_id=app_id,
            case_reference=case_ref,
            actor_id=actor_id,
            actor_label=actor_label,
            cta_primary_label="View Case",
            cta_primary_url=app_url,
        )
        await _maybe_send_email(
            db, notif.id, user_id,
            subject=f"VisaFlow — HR Review Update for {case_ref}",
            body_text=(
                f"Hi,\n\n{body}\n\nView your application: {app_url}\n\nVisaFlow Team"
            ),
            category_pref_field="notify_case_updates",
        )

    except Exception:
        logger.exception("fire_hr_approval_changed failed for application %s", app_id)
        await db.rollback()


async def fire_document_uploaded(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    document_name: str,
    application_id: Optional[uuid.UUID],
    case_reference: Optional[str],
    uploader_id: uuid.UUID,
    notify_hr_id: Optional[uuid.UUID] = None,
    notify_attorney_id: Optional[uuid.UUID] = None,
) -> None:
    try:
        uploader = await _get_user(db, uploader_id)
        actor_label = f"{uploader.first_name} {uploader.last_name}" if uploader else "Employee"
        doc_url = f"/documents/{document_id}"

        recipients: list[uuid.UUID] = []
        if notify_hr_id:
            recipients.append(notify_hr_id)
        if notify_attorney_id:
            recipients.append(notify_attorney_id)

        for recipient_id in recipients:
            notif = await _create_notification(
                db,
                user_id=recipient_id,
                notification_type="missing_document",
                category="case_update",
                priority="medium",
                title=f"New document uploaded — {document_name}",
                body=(
                    f"{actor_label} has uploaded \"{document_name}\" "
                    f"{('for case ' + case_reference) if case_reference else ''}."
                    " Please review."
                ),
                application_id=application_id,
                document_id=document_id,
                case_reference=case_reference,
                actor_id=uploader_id,
                actor_label=actor_label,
                cta_primary_label="Review Document",
                cta_primary_url=doc_url,
            )
            await _maybe_send_email(
                db, notif.id, recipient_id,
                subject=f"VisaFlow — Document Uploaded: {document_name}",
                body_text=(
                    f"Hi,\n\n{actor_label} uploaded \"{document_name}\".\n"
                    f"Review it: {doc_url}\n\nVisaFlow Team"
                ),
                category_pref_field="notify_document_updates",
            )

    except Exception:
        logger.exception("fire_document_uploaded failed for document %s", document_id)
        await db.rollback()


async def fire_document_verified(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    document_name: str,
    application_id: Optional[uuid.UUID],
    case_reference: Optional[str],
    employee_id: uuid.UUID,
    verifier_id: uuid.UUID,
) -> None:
    try:
        verifier = await _get_user(db, verifier_id)
        actor_label = f"{verifier.first_name} {verifier.last_name}" if verifier else "Staff"
        app_url = f"/applications/{application_id}" if application_id else "/documents"

        notif = await _create_notification(
            db,
            user_id=employee_id,
            notification_type="document_approved",
            category="case_update",
            priority="medium",
            title=f"Document verified — {document_name}",
            body=f"Your document \"{document_name}\" has been verified by {actor_label}.",
            application_id=application_id,
            document_id=document_id,
            case_reference=case_reference,
            actor_id=verifier_id,
            actor_label=actor_label,
            cta_primary_label="View Application",
            cta_primary_url=app_url,
        )
        await _maybe_send_email(
            db, notif.id, employee_id,
            subject=f"VisaFlow — Document Verified: {document_name}",
            body_text=(
                f"Hi,\n\nYour document \"{document_name}\" has been verified "
                f"by {actor_label}.\n\nView your application: {app_url}\n\nVisaFlow Team"
            ),
            category_pref_field="notify_document_updates",
        )

    except Exception:
        logger.exception("fire_document_verified failed for document %s", document_id)
        await db.rollback()


async def fire_document_rejected(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    document_name: str,
    application_id: Optional[uuid.UUID],
    case_reference: Optional[str],
    employee_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    rejection_reason: Optional[str] = None,
) -> None:
    try:
        reviewer = await _get_user(db, reviewer_id)
        actor_label = f"{reviewer.first_name} {reviewer.last_name}" if reviewer else "Staff"
        doc_url = f"/documents/{document_id}"

        body = f"Your document \"{document_name}\" was rejected by {actor_label}."
        if rejection_reason:
            body += f"\n\nReason: {rejection_reason}"
        body += "\n\nPlease upload a corrected version."

        notif = await _create_notification(
            db,
            user_id=employee_id,
            notification_type="missing_document",
            category="case_update",
            priority="urgent",
            title="Document rejected — action required",
            body=body,
            application_id=application_id,
            document_id=document_id,
            case_reference=case_reference,
            actor_id=reviewer_id,
            actor_label=actor_label,
            cta_primary_label="Re-upload Document",
            cta_primary_url=doc_url,
        )
        await _maybe_send_email(
            db, notif.id, employee_id,
            subject=f"VisaFlow — Action Required: Document Rejected ({document_name})",
            body_text=(
                f"Hi,\n\n{body}\n\nUpload here: {doc_url}\n\nVisaFlow Team"
            ),
            category_pref_field="notify_document_updates",
        )

    except Exception:
        logger.exception("fire_document_rejected failed for document %s", document_id)
        await db.rollback()


async def fire_deadline_approaching(
    db: AsyncSession,
    deadline: Deadline,
    *,
    days_remaining: int,
) -> None:
    # Cache before any DB ops to avoid expired-attribute issues
    deadline_id    = deadline.id
    deadline_title = deadline.title
    deadline_date  = deadline.due_date
    deadline_appid = deadline.application_id
    deadline_uid   = deadline.user_id

    try:
        if deadline.reminder_sent:
            return

        priority = "urgent" if days_remaining <= 7 else "high"
        app_url  = f"/applications/{deadline_appid}" if deadline_appid else "/deadlines"

        notif = await _create_notification(
            db,
            user_id=deadline_uid,
            notification_type="deadline_approaching",
            category="deadline",
            priority=priority,
            title=f"Deadline in {days_remaining} days — {deadline_title}",
            body=(
                f"The deadline \"{deadline_title}\" is due in {days_remaining} day(s) "
                f"({deadline_date.strftime('%b %d, %Y')}). Please take action."
            ),
            application_id=deadline_appid,
            cta_primary_label="View Deadline",
            cta_primary_url=app_url,
        )
        await _maybe_send_email(
            db, notif.id, deadline_uid,
            subject=f"VisaFlow — Deadline Approaching: {deadline_title} ({days_remaining} days)",
            body_text=(
                f"Hi,\n\nYou have a deadline coming up:\n\n"
                f"  {deadline_title}\n"
                f"  Due: {deadline_date.strftime('%B %d, %Y')}\n"
                f"  Days remaining: {days_remaining}\n\n"
                f"View it here: {app_url}\n\nVisaFlow Team"
            ),
            category_pref_field="notify_deadlines",
        )

        deadline.reminder_sent = True
        await db.flush()

    except Exception:
        logger.exception("fire_deadline_approaching failed for deadline %s", deadline_id)
        await db.rollback()


async def fire_approval_pending(
    db: AsyncSession,
    application: Application,
    *,
    hr_id: uuid.UUID,
    employee_name: str,
    deadline_days: Optional[int] = None,
) -> None:
    app_id  = application.id
    app_num = application.application_number

    try:
        case_ref = app_num
        app_url  = f"/employer/cases/{app_id}"

        deadline_clause = (
            f" Deadline in {deadline_days} day(s)." if deadline_days is not None else ""
        )

        notif = await _create_notification(
            db,
            user_id=hr_id,
            notification_type="approval_pending",
            category="approval",
            priority="urgent" if (deadline_days is not None and deadline_days <= 3) else "high",
            title=f"{employee_name}'s petition awaiting your approval",
            body=(
                f"Case {case_ref} for {employee_name} is ready for HR review "
                f"before attorney filing.{deadline_clause}"
            ),
            application_id=app_id,
            case_reference=case_ref,
            actor_label=employee_name,
            cta_primary_label="Review Now",
            cta_primary_url=app_url,
            cta_secondary_label="Delegate",
        )
        await _maybe_send_email(
            db, notif.id, hr_id,
            subject=f"VisaFlow — Approval Needed: {case_ref}",
            body_text=(
                f"Hi,\n\n{employee_name}'s case {case_ref} needs your approval"
                f"{deadline_clause}\n\nReview it: {app_url}\n\nVisaFlow Team"
            ),
            category_pref_field="notify_case_updates",
        )

    except Exception:
        logger.exception("fire_approval_pending failed for application %s", app_id)
        await db.rollback()


async def fire_approval_resolved(
    db: AsyncSession,
    application: Application,
    *,
    employee_id: uuid.UUID,
    decision: str,
    actor_id: uuid.UUID,
) -> None:
    app_id  = application.id
    app_num = application.application_number

    try:
        actor = await _get_user(db, actor_id)
        actor_label = f"{actor.first_name} {actor.last_name}" if actor else "HR"
        case_ref = app_num
        app_url  = f"/applications/{app_id}"

        labels = {
            "approved":          ("Your petition was approved by HR", "high"),
            "rejected":          ("Your petition was rejected by HR", "urgent"),
            "changes_requested": ("HR requested changes to your petition", "urgent"),
        }
        title, priority = labels.get(decision, (f"HR decision on {case_ref}", "medium"))

        notif = await _create_notification(
            db,
            user_id=employee_id,
            notification_type="approval_resolved",
            category="approval",
            priority=priority,
            title=title,
            body=f"{actor_label} has resolved the HR review for case {case_ref}.",
            application_id=app_id,
            case_reference=case_ref,
            actor_id=actor_id,
            actor_label=actor_label,
            cta_primary_label="View Case",
            cta_primary_url=app_url,
        )
        await _maybe_send_email(
            db, notif.id, employee_id,
            subject=f"VisaFlow — HR Decision on {case_ref}",
            body_text=f"Hi,\n\n{title}.\n\nView it: {app_url}\n\nVisaFlow Team",
            category_pref_field="notify_case_updates",
        )

    except Exception:
        logger.exception("fire_approval_resolved failed for application %s", app_id)
        await db.rollback()


async def fire_employee_onboarded(
    db: AsyncSession,
    *,
    hr_id: uuid.UUID,
    employee_id: uuid.UUID,
    employee_name: str,
) -> None:
    try:
        notif = await _create_notification(
            db,
            user_id=hr_id,
            notification_type="employee_onboarded",
            category="employee",
            priority="high",
            title="New employee accepted invitation",
            body=(
                f"{employee_name} accepted your company invite and completed "
                "profile setup. Assign a case attorney to get started."
            ),
            actor_id=employee_id,
            actor_label=employee_name,
            cta_primary_label="View Employee",
            cta_primary_url="/employer/employees",
        )
        await _maybe_send_email(
            db, notif.id, hr_id,
            subject=f"VisaFlow — {employee_name} Joined Your Company",
            body_text=(
                f"Hi,\n\n{employee_name} accepted your invitation and completed "
                f"setup.\n\nView the employee roster: /employer/employees\n\nVisaFlow Team"
            ),
            category_pref_field="notify_case_updates",
        )

    except Exception:
        logger.exception("fire_employee_onboarded failed for employee %s", employee_id)
        await db.rollback()


async def fire_employee_profile_updated(
    db: AsyncSession,
    *,
    hr_id: uuid.UUID,
    employee_id: uuid.UUID,
    employee_name: str,
    fields_changed: Optional[list[str]] = None,
) -> None:
    try:
        changed = ", ".join(fields_changed) if fields_changed else "their profile"
        await _create_notification(
            db,
            user_id=hr_id,
            notification_type="employee_profile_updated",
            category="employee",
            priority="low",
            title="Employee profile updated",
            body=f"{employee_name} updated {changed}. Review changes if needed.",
            actor_id=employee_id,
            actor_label=employee_name,
            cta_primary_label="View Employee",
            cta_primary_url="/employer/employees",
        )
        # Low priority — in-app only, no email

    except Exception:
        logger.exception("fire_employee_profile_updated failed for employee %s", employee_id)
        await db.rollback()


async def fire_compliance_alert(
    db: AsyncSession,
    *,
    hr_id: uuid.UUID,
    title: str,
    body: str,
    affected_count: Optional[int] = None,
    cta_url: str = "/employer/employees",
    priority: str = "urgent",
) -> None:
    try:
        full_body = body
        if affected_count is not None:
            full_body += f" ({affected_count} employee{'s' if affected_count != 1 else ''} affected.)"

        notif = await _create_notification(
            db,
            user_id=hr_id,
            notification_type="compliance_alert",
            category="compliance",
            priority=priority,
            title=title,
            body=full_body,
            cta_primary_label="View Employees",
            cta_primary_url=cta_url,
        )
        await _maybe_send_email(
            db, notif.id, hr_id,
            subject=f"VisaFlow Compliance Alert — {title}",
            body_text=f"Hi,\n\n{full_body}\n\nView details: {cta_url}\n\nVisaFlow Team",
            category_pref_field="notify_compliance_alerts",
        )

    except Exception:
        logger.exception("fire_compliance_alert failed for hr %s", hr_id)
        await db.rollback()