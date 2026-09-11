"""
subscription_renewal_service.py
================================
Daily job: find subscriptions whose current_period_end is approaching
(or just passed) and email the org admin / subscriber to renew.

Idempotent via audit_logs rows (action=subscription.renewal_reminder).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.email import send_email
from app.models.visamodels import (
    AuditLog,
    EmployerProfile,
    OrganizationMember,
    User,
    UserSubscription,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Days before period end to remind (inclusive). Also 0 = due today, -1 = overdue day 1.
RENEWAL_THRESHOLDS_DAYS: Sequence[int] = (14, 7, 3, 1, 0, -1)


async def _already_sent(
    db: AsyncSession,
    subscription_id,
    threshold_days: int,
) -> bool:
    marker = f"threshold_days={threshold_days}"
    row = (
        await db.execute(
            select(AuditLog.id).where(
                AuditLog.action == "subscription.renewal_reminder",
                AuditLog.resource_id == subscription_id,
                AuditLog.description.contains(marker),
            ).limit(1)
        )
    ).scalar_one_or_none()
    return row is not None


async def _recipient_emails_for_subscription(
    db: AsyncSession,
    sub: UserSubscription,
) -> list[tuple[str, str]]:
    """
    Prefer active org_admins for the employer owned by the subscriber;
    fall back to the subscriber themselves.
    Returns list of (email, display_name).
    """
    recipients: list[tuple[str, str]] = []

    ep = (
        await db.execute(
            select(EmployerProfile).where(EmployerProfile.user_id == sub.user_id)
        )
    ).scalar_one_or_none()

    if ep:
        members = (
            await db.execute(
                select(User)
                .join(OrganizationMember, OrganizationMember.user_id == User.id)
                .where(
                    OrganizationMember.employer_profile_id == ep.id,
                    OrganizationMember.is_active == True,  # noqa: E712
                    OrganizationMember.org_role == "org_admin",
                    User.is_active == True,  # noqa: E712
                    User.email.is_not(None),
                )
            )
        ).scalars().all()
        for u in members:
            name = f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email
            recipients.append((u.email, name))

    if not recipients:
        user = await db.get(User, sub.user_id)
        if user and user.email:
            name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
            recipients.append((user.email, name))

    # de-dupe by email
    seen = set()
    unique: list[tuple[str, str]] = []
    for email, name in recipients:
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((email, name))
    return unique


async def check_and_send_subscription_renewal_reminders(db: AsyncSession) -> int:
    """
    Send renewal reminder emails for active/trialing subscriptions near period end.
    Returns number of emails attempted.
    """
    now = datetime.now(timezone.utc)
    # Look at subscriptions ending within the next 14 days or overdue by 2 days
    window_start = now - timedelta(days=2)
    window_end = now + timedelta(days=15)

    subs = (
        await db.execute(
            select(UserSubscription)
            .options(selectinload(UserSubscription.plan))
            .where(
                UserSubscription.status.in_(["active", "trialing", "past_due"]),
                UserSubscription.current_period_end.is_not(None),
                UserSubscription.current_period_end >= window_start,
                UserSubscription.current_period_end <= window_end,
            )
        )
    ).scalars().all()

    sent = 0
    frontend = getattr(settings, "FRONTEND_URL", "") or "https://app.vyuflo.com"

    for sub in subs:
        period_end = sub.current_period_end
        if not period_end:
            continue
        # Normalize aware
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)

        days_remaining = (period_end.date() - now.date()).days
        if days_remaining not in RENEWAL_THRESHOLDS_DAYS:
            continue
        if await _already_sent(db, sub.id, days_remaining):
            continue

        plan_name = sub.plan.name if sub.plan else "your plan"
        cycle = sub.billing_cycle or "monthly"
        end_label = period_end.strftime("%B %d, %Y")

        if days_remaining > 0:
            subject = f"Renew your Vyuflo {plan_name} plan — {days_remaining} day(s) left"
            urgency = f"expires in {days_remaining} day(s) on {end_label}"
        elif days_remaining == 0:
            subject = f"Renew your Vyuflo {plan_name} plan — due today"
            urgency = f"is due today ({end_label})"
        else:
            subject = f"Renew your Vyuflo {plan_name} plan — overdue"
            urgency = f"ended on {end_label}"

        recipients = await _recipient_emails_for_subscription(db, sub)
        if not recipients:
            continue

        renew_url = f"{frontend.rstrip('/')}/admin/plans"
        for email, name in recipients:
            body = (
                f"Hi {name},\n\n"
                f"Your organization's Vyuflo subscription ({plan_name}, {cycle}) {urgency}.\n\n"
                f"Please renew to keep uninterrupted access:\n{renew_url}\n\n"
                f"— Vyuflo"
            )
            body_html = (
                f"<p>Hi {name},</p>"
                f"<p>Your organization's Vyuflo subscription "
                f"(<strong>{plan_name}</strong>, {cycle}) {urgency}.</p>"
                f"<p><a href=\"{renew_url}\">Renew your plan</a></p>"
                f"<p>— Vyuflo</p>"
            )
            try:
                await send_email(
                    to=email,
                    subject=subject,
                    body=body,
                    body_html=body_html,
                )
                sent += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("Renewal email failed for %s: %s", email, exc)

        db.add(
            AuditLog(
                actor_id=None,
                actor_type="system",
                action="subscription.renewal_reminder",
                resource_type="user_subscription",
                resource_id=sub.id,
                description=(
                    f"Renewal reminder sent threshold_days={days_remaining} "
                    f"plan={plan_name} recipients={len(recipients)}"
                ),
                severity="info",
            )
        )

        # Mark overdue subscriptions as past_due once reminder fires for day -1
        if days_remaining < 0 and sub.status in ("active", "trialing"):
            sub.status = "past_due"
            sub.updated_at = now

    await db.commit()
    return sent
