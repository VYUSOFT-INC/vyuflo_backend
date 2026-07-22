"""
app/services/notification_template.py  ← FINAL CORRECT VERSION
Save as: app/services/notification_template.py

Your routes/notification_templates.py already imports from this exact path:
  from app.services.notification_template import (...)

Matches the Notification Templates screen:
  - List with template name, channel, trigger event (event_key),
    last modified date + "by [name]", status toggle
  - Search by name / event_key
  - Filter by channel / trigger / status
  - Pagination: "Showing 1 to 10 of 24 results"
"""
from __future__ import annotations

import json
import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import ConflictException, NotFoundException
from app.models.visamodels import NotificationTemplate, User


# =============================================================================
# CREATE
# =============================================================================
async def service_create_template(
    db: AsyncSession, event_key: str, name: str, description: Optional[str],
    channel: str, subject: Optional[str], body_html: Optional[str],
    body_text: str, available_placeholders: Optional[str],
    category: str, is_active: bool, created_by: uuid.UUID,
) -> NotificationTemplate:
    exists = (await db.execute(
        select(NotificationTemplate).where(NotificationTemplate.event_key == event_key)
    )).scalar_one_or_none()
    if exists:
        raise ConflictException(f"Template '{event_key}' already exists.")

    t = NotificationTemplate(
        event_key=event_key, name=name, description=description,
        channel=channel, subject=subject, body_html=body_html,
        body_text=body_text, available_placeholders=available_placeholders,
        category=category, is_active=is_active,
        created_by=created_by, modified_by=created_by,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


# =============================================================================
# LIST  (paginated + filterable + searchable)
# Powers: Search box + All Channels / All Triggers / All Statuses filters
# =============================================================================
async def service_list_templates(
    db: AsyncSession,
    channel:   Optional[str]  = None,   # "email" | "sms" | "in_app" | "push"
    trigger:   Optional[str]  = None,   # partial event_key match e.g. "status_changed"
    is_active: Optional[bool] = None,   # True / False / None (all)
    search:    Optional[str]  = None,   # searches name + event_key + description
    page:      int            = 1,
    limit:     int            = 10,
) -> dict:
    stmt = select(NotificationTemplate).order_by(
        NotificationTemplate.category, NotificationTemplate.name
    )

    if channel   is not None: stmt = stmt.where(NotificationTemplate.channel   == channel)
    if is_active is not None: stmt = stmt.where(NotificationTemplate.is_active == is_active)
    if trigger:
        stmt = stmt.where(NotificationTemplate.event_key.ilike(f"%{trigger}%"))
    if search:
        t = f"%{search}%"
        stmt = stmt.where(
            NotificationTemplate.name.ilike(t)
            | NotificationTemplate.event_key.ilike(t)
            | NotificationTemplate.description.ilike(t)
        )

    total = (await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )).scalar_one()

    items = (await db.execute(
        stmt.offset((page - 1) * limit).limit(limit)
    )).scalars().all()

    # Resolve modified_by → user name for "by Sarah J." column
    modifier_ids = [t.modified_by for t in items if t.modified_by]
    name_map: dict = {}
    if modifier_ids:
        users = (await db.execute(
            select(User).where(User.id.in_(modifier_ids))
        )).scalars().all()
        name_map = {
            u.id: f"{u.first_name} {u.last_name[0]}." if u.last_name else u.first_name
            for u in users
        }

    # Attach last_modified_by_name to each template (not a DB column — computed)
    result_items = []
    for tmpl in items:
        tmpl._last_modified_by_name = name_map.get(tmpl.modified_by)
        result_items.append(tmpl)

    return {
        "items":       result_items,
        "total":       total,
        "page":        page,
        "limit":       limit,
        "total_pages": max(1, (total + limit - 1) // limit),
    }


# =============================================================================
# GET BY ID
# =============================================================================
async def service_get_template(
    db: AsyncSession, template_id: uuid.UUID
) -> NotificationTemplate:
    t = (await db.execute(
        select(NotificationTemplate).where(NotificationTemplate.id == template_id)
    )).scalar_one_or_none()
    if not t:
        raise NotFoundException(f"Template '{template_id}' not found.")
    return t


# =============================================================================
# GET BY EVENT KEY  (used by dispatch and /by-key/ route)
# =============================================================================
async def service_get_template_by_event_key(
    db: AsyncSession, event_key: str
) -> NotificationTemplate:
    t = (await db.execute(
        select(NotificationTemplate).where(NotificationTemplate.event_key == event_key)
    )).scalar_one_or_none()
    if not t:
        raise NotFoundException(f"Template with event_key '{event_key}' not found.")
    return t


# =============================================================================
# UPDATE  (PATCH — content only; event_key + channel are immutable)
# =============================================================================
async def service_update_template(
    db: AsyncSession, template_id: uuid.UUID,
    name: Optional[str], description: Optional[str],
    subject: Optional[str], body_html: Optional[str],
    body_text: Optional[str], available_placeholders: Optional[str],
    is_active: Optional[bool], modified_by: uuid.UUID,
) -> NotificationTemplate:
    t = await service_get_template(db, template_id)
    if name                   is not None: t.name                   = name
    if description            is not None: t.description            = description
    if subject                is not None: t.subject                = subject
    if body_html              is not None: t.body_html              = body_html
    if body_text              is not None: t.body_text              = body_text
    if available_placeholders is not None: t.available_placeholders = available_placeholders
    if is_active              is not None: t.is_active              = is_active
    t.modified_by = modified_by
    await db.commit()
    await db.refresh(t)
    return t


# =============================================================================
# TOGGLE  (PATCH /{id}/toggle) — the Status on/off switch in the list
# =============================================================================
async def service_toggle_template(
    db: AsyncSession, template_id: uuid.UUID,
    is_active: bool, modified_by: uuid.UUID,
) -> NotificationTemplate:
    t = await service_get_template(db, template_id)
    t.is_active   = is_active
    t.modified_by = modified_by
    await db.commit()
    await db.refresh(t)
    return t


# =============================================================================
# PREVIEW  (POST /{id}/preview) — renders {{placeholders}}, no DB writes
# =============================================================================
async def service_preview_template(
    db: AsyncSession, template_id: uuid.UUID, context: dict
) -> dict:
    t = await service_get_template(db, template_id)

    rendered_subject  = render_body(t.subject or "",  context)
    rendered_body     = render_body(t.body_text,       context)
    rendered_html     = render_body(t.body_html or "", context)

    available = []
    if t.available_placeholders:
        try:
            available = json.loads(t.available_placeholders)
        except Exception:
            available = []

    # Tell the admin UI which vars were not supplied in context
    missing_vars = [p for p in available if p.strip("{}") not in context]

    return {
        "template_id":  str(t.id),
        "event_key":    t.event_key,
        "channel":      t.channel,
        "subject":      rendered_subject,
        "body_text":    rendered_body,
        "body_html":    rendered_html,
        "missing_vars": missing_vars,
    }


# =============================================================================
# RENDER HELPER — str.replace() only, deliberately NOT Jinja2
# Admin-editable templates + Jinja2 = SSTI vulnerability
# =============================================================================
def render_body(body: str, context: dict) -> str:
    """
    Replace {{key}} placeholders with context values.
    Example:
        render_body("Dear {{user_name}}", {"user_name": "John"}) → "Dear John"
    """
    for key, value in context.items():
        body = body.replace(f"{{{{{key}}}}}", str(value))
    return body


# =============================================================================
# DISPATCH HELPER — called from other services to fire a notification
# =============================================================================
async def dispatch_notification_from_template(
    db: AsyncSession, event_key: str, user_id: uuid.UUID, context: dict,
) -> Optional[dict]:
    """
    Looks up template, checks is_active, renders it.
    Returns rendered dict or None (silent skip if missing/disabled).

    Usage in application_services.py:
        content = await dispatch_notification_from_template(
            db, "case_status_updated", user_id,
            {"user_name": "John", "application_number": "APP-001", "new_status": "approved"}
        )
        if content:
            notif = Notification(user_id=user_id, title=content["title"], ...)
            db.add(notif)
    """
    try:
        t = await service_get_template_by_event_key(db, event_key)
    except NotFoundException:
        return None

    if not t.is_active:
        return None

    return {
        "title":     render_body(t.name,         context),
        "subject":   render_body(t.subject or "",  context),
        "body":      render_body(t.body_text,      context),
        "body_html": render_body(t.body_html or "", context),
        "channel":   t.channel,
        "category":  t.category,
    }


# =============================================================================
# SEED DATA — covers all trigger events visible in the Notification Templates
# screen: Status_Changed_Approved, Doc_Status_Missing, Interview_Date_Set, etc.
# =============================================================================
NOTIFICATION_TEMPLATES_SEED = [
    {
        "event_key": "case_status_updated.approved",
        "name": "Visa Application Approved",
        "description": "Sent to applicant upon final approval",
        "channel": "email",
        "subject": "Congratulations! Your {{visa_type}} application has been approved",
        "body_html": "<p>Dear {{user_name}},</p><p>Your application <strong>{{application_number}}</strong> has been <strong>approved</strong>.</p>",
        "body_text": "Dear {{user_name}},\n\nYour {{visa_type}} application {{application_number}} has been approved.",
        "available_placeholders": '["{{user_name}}", "{{application_number}}", "{{visa_type}}"]',
        "category": "case_update", "is_active": True,
    },
    {
        "event_key": "missing_document",
        "name": "Missing Documents Alert",
        "description": "Dashboard notification for required docs",
        "channel": "in_app",
        "subject": None,
        "body_html": None,
        "body_text": "Your application {{application_number}} is missing: {{document_name}}. Please upload it.",
        "available_placeholders": '["{{user_name}}", "{{application_number}}", "{{document_name}}"]',
        "category": "case_update", "is_active": True,
    },
    {
        "event_key": "interview_scheduled",
        "name": "Interview Scheduled",
        "description": "SMS reminder 24h before interview",
        "channel": "sms",
        "subject": None,
        "body_html": None,
        "body_text": "Reminder: Your {{visa_type}} interview is on {{interview_date}} at {{interview_time}}. Good luck!",
        "available_placeholders": '["{{user_name}}", "{{visa_type}}", "{{interview_date}}", "{{interview_time}}"]',
        "category": "deadline", "is_active": False,
    },
    {
        "event_key": "deadline_approaching",
        "name": "Deadline Approaching",
        "description": "Sent when a deadline is within the alert window",
        "channel": "in_app",
        "subject": None,
        "body_html": None,
        "body_text": "{{deadline_title}} is due on {{deadline_date}} ({{days_remaining}} days remaining).",
        "available_placeholders": '["{{user_name}}", "{{deadline_title}}", "{{deadline_date}}", "{{days_remaining}}"]',
        "category": "deadline", "is_active": True,
    },
    {
        "event_key": "case_status_updated",
        "name": "Case Status Updated",
        "description": "Sent when any application status changes",
        "channel": "in_app",
        "subject": None,
        "body_html": None,
        "body_text": "Your {{visa_type}} application {{application_number}} status changed to: {{new_status}}.",
        "available_placeholders": '["{{user_name}}", "{{application_number}}", "{{visa_type}}", "{{new_status}}"]',
        "category": "case_update", "is_active": True,
    },
    {
        "event_key": "security_alert",
        "name": "Security Alert — New Login",
        "description": "Sent on new device login",
        "channel": "email",
        "subject": "Security Alert: New login to your Vyuflo account",
        "body_html": "<p>Dear {{user_name}},</p><p>New login from <strong>{{device}}</strong> at {{login_time}}.</p>",
        "body_text": "Dear {{user_name}},\n\nNew login from {{device}} at {{login_time}} ({{ip_address}}).",
        "available_placeholders": '["{{user_name}}", "{{device}}", "{{login_time}}", "{{ip_address}}"]',
        "category": "security", "is_active": True,
    },
    {
        "event_key": "weekly_summary",
        "name": "Weekly Case Summary",
        "description": "Weekly digest of case activity",
        "channel": "email",
        "subject": "Your Weekly Vyuflo Summary — {{week_range}}",
        "body_html": "<p>Dear {{user_name}},</p><p>{{summary_content}}</p>",
        "body_text": "Dear {{user_name}},\n\nYour weekly summary for {{week_range}}:\n{{summary_content}}",
        "available_placeholders": '["{{user_name}}", "{{summary_content}}", "{{week_range}}"]',
        "category": "case_update", "is_active": True,
    },
    {
        "event_key": "payment_receipt",
        "name": "Payment Receipt",
        "description": "Sent after a successful payment",
        "channel": "email",
        "subject": "Payment Confirmed — {{amount}} for {{visa_type}}",
        "body_html": "<p>Dear {{user_name}},</p><p>Payment of <strong>{{amount}}</strong> confirmed.</p>",
        "body_text": "Dear {{user_name}},\n\nPayment of {{amount}} confirmed on {{payment_date}}.",
        "available_placeholders": '["{{user_name}}", "{{amount}}", "{{payment_date}}", "{{visa_type}}"]',
        "category": "billing", "is_active": True,
    },
]


async def seed_notification_templates(db: AsyncSession) -> None:
    """Idempotent — skips already-seeded event_keys."""
    for item in NOTIFICATION_TEMPLATES_SEED:
        exists = (await db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.event_key == item["event_key"]
            )
        )).scalar_one_or_none()
        if not exists:
            db.add(NotificationTemplate(**item))
    await db.commit()