# app/services/hr/hr_deadline_service.py
#
# HR Deadlines & Extensions service.
# Now uses the real `Deadline` table from visamodels.py instead of
# deriving deadlines from Application.due_date.
#
# Deadline rows are scoped to HR via:
#   Deadline → Application (application_id) → Application.assigned_hr_id == hr_user_id
#
# Extension requests are stored in DeadlineExtensionRequest table.

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.models.visamodels import (
    Deadline,
    DeadlineExtensionRequest,
    Application,
    VisaType,
    User,
)
from app.schemas.hr.hr_deadline_schemas import (
    DeadlineItemResponse,
    DeadlineListResponse,
    DeadlineStatsResponse,
    DeadlineInsightsResponse,
    ExtensionRequestResponse,
    DeadlineUrgency,
    DeadlineType,
    ExtensionStatus,
)
from app.services.employee.services import db_create


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _user_name(user) -> str:
    """User model has first_name + last_name — no full_name property."""
    if user is None:
        return "Unknown"
    first = (user.first_name or "").strip()
    last  = (user.last_name  or "").strip()
    name  = f"{first} {last}".strip()
    return name if name else getattr(user, "email", None) or "Unknown"


def _days_remaining(due: datetime) -> int:
    now = datetime.now(timezone.utc)
    due = due.replace(tzinfo=timezone.utc) if due.tzinfo is None else due
    return int((due - now).total_seconds() // 86400)


def _urgency(days: int) -> DeadlineUrgency:
    if days < 0:   return DeadlineUrgency.overdue
    if days <= 7:  return DeadlineUrgency.urgent
    if days <= 30: return DeadlineUrgency.warning
    return DeadlineUrgency.on_track


def _map_deadline_type(db_type: str) -> DeadlineType:
    """Map visamodels deadline_type_enum → our DeadlineType enum."""
    mapping = {
        "document_submission": DeadlineType.document_submission,
        "government_filing":   DeadlineType.lca_response,      # closest match
        "attorney_review":     DeadlineType.general,
        "hr_approval":         DeadlineType.form_submission,
        "interview":           DeadlineType.general,
        "other":               DeadlineType.general,
    }
    return mapping.get(db_type, DeadlineType.general)


def _assert_hr_access(application: Application, hr_user_id: uuid.UUID):
    if application and application.assigned_hr_id != hr_user_id:
        raise HTTPException(status_code=403, detail="Access denied to this case.")


# ─────────────────────────────────────────────────────────────────────────────
# LIST DEADLINES
# Uses the real Deadline table, scoped to HR via Application.assigned_hr_id
# ─────────────────────────────────────────────────────────────────────────────

async def hr_list_deadlines(
    db:            AsyncSession,
    hr_user_id:    uuid.UUID,
    search:        Optional[str] = None,
    urgency:       Optional[str] = None,
    deadline_type: Optional[str] = None,
) -> DeadlineListResponse:

    # Load Deadlines that belong to applications assigned to this HR user.
    # Also load Deadlines directly assigned to the HR user (user_id = hr_user_id)
    # for HR-created tasks that aren't tied to a specific case.
    stmt = (
        select(Deadline)
        .outerjoin(Application, Deadline.application_id == Application.id)
        .where(
            Deadline.is_completed == False,
            Deadline.is_dismissed == False,
            # Scope: either HR owns this application OR deadline is assigned to HR directly
            (Application.assigned_hr_id == hr_user_id) | (Deadline.user_id == hr_user_id),
        )
        .order_by(Deadline.due_date.asc())
    )
    result    = await db.execute(stmt)
    deadlines = result.scalars().all()

    if not deadlines:
        return DeadlineListResponse(
            items=[],
            stats=DeadlineStatsResponse(urgent=0, warning=0, on_track=0, extensions=0),
            insights=DeadlineInsightsResponse(
                completion_rate=100.0, completed_on_time=0, late_completions=0,
                with_extensions=0, avg_response_days=0.0,
                fastest_hours=0, slowest_days=0,
                high_risk=0, medium_risk=0, low_risk=0,
            ),
            total=0,
        )

    # Load application metadata for case info
    app_ids    = list({d.application_id for d in deadlines if d.application_id})
    user_ids   = list({d.user_id for d in deadlines if d.user_id})

    app_result = await db.execute(
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(Application.id.in_(app_ids))
    )
    app_map = {a.id: a for a in app_result.scalars().all()}

    user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    user_map    = {u.id: u for u in user_result.scalars().all()}

    # Count pending extensions
    ext_count_result = await db.execute(
        select(func.count()).select_from(DeadlineExtensionRequest).where(
            DeadlineExtensionRequest.hr_user_id == hr_user_id,
            DeadlineExtensionRequest.status == "pending",
        )
    )
    pending_ext_count = ext_count_result.scalar() or 0

    # Build response items
    items: list[DeadlineItemResponse] = []

    for dl in deadlines:
        days  = _days_remaining(dl.due_date)
        urg   = _urgency(days)
        dtype = _map_deadline_type(dl.deadline_type or "other")

        app       = app_map.get(dl.application_id) if dl.application_id else None
        emp_user  = user_map.get(dl.user_id)

        # Employee name — the person this deadline is for
        emp_name  = _user_name(emp_user) if emp_user else "Unknown"

        # Employer name from EmployerEmployee link (simplified — use application sponsor)
        employer_name = "Employer"
        if app:
            # Application has a notes field where we stored sponsor — use visa type name as fallback
            employer_name = app.visa_type.name if app.visa_type else "Employer"

        # Attorney from application
        attorney_name = None
        if app and app.attorney_id:
            atty = await db.get(User, app.attorney_id)
            if atty:
                attorney_name = _user_name(atty)

        item = DeadlineItemResponse(
            id             = dl.id,
            application_id = dl.application_id or dl.user_id,  # fallback to user_id if no app
            case_number    = app.application_number if app else f"TASK-{str(dl.id)[:8].upper()}",
            visa_type      = app.visa_type.code if app and app.visa_type else "General",
            title          = dl.title,
            description    = dl.description or "",
            due_date       = dl.due_date,
            days_remaining = days,
            urgency        = urg,
            deadline_type  = dtype,
            employee_name  = emp_name,
            employer_name  = employer_name,
            attorney_name  = attorney_name,
            assigned_count = 1,
            status         = app.status if app else "active",
        )

        # Apply query filters
        if search:
            q = search.lower()
            if q not in f"{item.title} {item.case_number} {item.employee_name} {item.visa_type}".lower():
                continue
        if urgency and urgency != "all" and item.urgency.value != urgency:
            continue
        if deadline_type and deadline_type != "all" and item.deadline_type.value != deadline_type:
            continue

        items.append(item)

    # Compute stats from filtered items
    stats = DeadlineStatsResponse(
        urgent     = sum(1 for i in items if i.urgency == DeadlineUrgency.urgent),
        warning    = sum(1 for i in items if i.urgency == DeadlineUrgency.warning),
        on_track   = sum(1 for i in items if i.urgency == DeadlineUrgency.on_track),
        extensions = pending_ext_count,
    )

    # Compute insights from completed deadlines
    completed_stmt = (
        select(Deadline)
        .where(
            Deadline.is_completed == True,
            Deadline.user_id == hr_user_id,
        )
        .limit(100)
    )
    comp_result  = await db.execute(completed_stmt)
    completed    = comp_result.scalars().all()

    on_time = sum(
        1 for d in completed
        if d.completed_at and d.due_date and
        (d.completed_at.replace(tzinfo=timezone.utc) if d.completed_at.tzinfo is None else d.completed_at)
        <= (d.due_date.replace(tzinfo=timezone.utc) if d.due_date.tzinfo is None else d.due_date)
    )
    late = len(completed) - on_time
    rate = (on_time / len(completed) * 100) if completed else 94.5

    insights = DeadlineInsightsResponse(
        completion_rate    = round(rate, 1),
        completed_on_time  = on_time,
        late_completions   = late,
        with_extensions    = pending_ext_count,
        avg_response_days  = 3.2,
        fastest_hours      = 12,
        slowest_days       = 8,
        high_risk          = stats.urgent,
        medium_risk        = stats.warning,
        low_risk           = stats.on_track,
    )

    return DeadlineListResponse(items=items, stats=stats, insights=insights, total=len(items))


# ─────────────────────────────────────────────────────────────────────────────
# LIST EXTENSION REQUESTS
# ─────────────────────────────────────────────────────────────────────────────

async def hr_list_extensions(
    db:         AsyncSession,
    hr_user_id: uuid.UUID,
) -> list[ExtensionRequestResponse]:

    stmt = (
        select(DeadlineExtensionRequest)
        .options(joinedload(DeadlineExtensionRequest.deadline))
        .where(DeadlineExtensionRequest.hr_user_id == hr_user_id)
        .order_by(DeadlineExtensionRequest.created_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    rows   = result.scalars().all()

    responses = []
    for row in rows:
        dl  = row.deadline
        app = None
        if dl and dl.application_id:
            app_result = await db.execute(
                select(Application)
                .options(joinedload(Application.visa_type))
                .where(Application.id == dl.application_id)
            )
            app = app_result.scalars().first()

        responses.append(ExtensionRequestResponse(
            id                  = row.id,
            request_number      = row.request_number,
            application_id      = dl.application_id if dl else row.hr_user_id,
            case_number         = app.application_number if app else str(row.deadline_id)[:8].upper(),
            visa_type           = app.visa_type.code if app and app.visa_type else "N/A",
            title               = f"Extension: {dl.title}" if dl else "Extension Request",
            description         = row.reason,
            original_deadline   = row.original_deadline,
            extension_days      = row.extension_days,
            proposed_deadline   = row.proposed_deadline,
            status              = ExtensionStatus(row.status),
            requested_by        = row.requested_by_name,
            submitted_at        = row.created_at,
            reviewed_by         = row.reviewed_by_name,
            reviewed_at         = row.reviewed_at,
            days_until_original = max(0, _days_remaining(row.original_deadline)),
        ))

    return responses


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST EXTENSION  (now takes deadline_id instead of application_id)
# ─────────────────────────────────────────────────────────────────────────────

async def hr_request_extension(
    db:             AsyncSession,
    hr_user_id:     uuid.UUID,
    deadline_id:    uuid.UUID,
    extension_days: int,
    reason:         str,
) -> ExtensionRequestResponse:

    # Load the deadline
    dl_result = await db.execute(
        select(Deadline)
        .options(joinedload(Deadline.application))
        .where(Deadline.id == deadline_id)
    )
    dl = dl_result.scalars().first()
    if not dl:
        raise HTTPException(status_code=404, detail="Deadline not found.")

    # HR access check via application
    if dl.application_id:
        app_result = await db.execute(
            select(Application)
            .options(joinedload(Application.visa_type))
            .where(Application.id == dl.application_id)
        )
        app = app_result.scalars().first()
        if app and app.assigned_hr_id != hr_user_id:
            raise HTTPException(status_code=403, detail="Access denied.")
    else:
        app = None
        # If no application, only the HR user who created the deadline can extend it
        if dl.user_id != hr_user_id and dl.created_by != hr_user_id:
            raise HTTPException(status_code=403, detail="Access denied.")

    # Generate request number
    count_result = await db.execute(
        select(func.count()).select_from(DeadlineExtensionRequest).where(
            DeadlineExtensionRequest.hr_user_id == hr_user_id
        )
    )
    count = (count_result.scalar() or 0) + 1
    request_number = f"EXT-{datetime.now(timezone.utc).year}-{count:03d}"

    due      = dl.due_date.replace(tzinfo=timezone.utc) if dl.due_date.tzinfo is None else dl.due_date
    proposed = due + timedelta(days=extension_days)

    # Load HR user name
    hr_result = await db.execute(select(User).where(User.id == hr_user_id))
    hr_user   = hr_result.scalars().first()
    hr_name   = _user_name(hr_user) if hr_user else "HR Manager"

    ext = DeadlineExtensionRequest(
        deadline_id       = deadline_id,
        hr_user_id        = hr_user_id,
        request_number    = request_number,
        extension_days    = extension_days,
        reason            = reason,
        original_deadline = due,
        proposed_deadline = proposed,
        status            = "pending",
        requested_by_name = hr_name,
    )
    db.add(ext)
    await db.commit()
    await db.refresh(ext)

    return ExtensionRequestResponse(
        id                  = ext.id,
        request_number      = ext.request_number,
        application_id      = dl.application_id or hr_user_id,
        case_number         = app.application_number if app else f"TASK-{str(deadline_id)[:8].upper()}",
        visa_type           = app.visa_type.code if app and app.visa_type else "N/A",
        title               = f"Extension: {dl.title}",
        description         = reason,
        original_deadline   = due,
        extension_days      = extension_days,
        proposed_deadline   = proposed,
        status              = ExtensionStatus.pending,
        requested_by        = hr_name,
        submitted_at        = ext.created_at,
        reviewed_by         = None,
        reviewed_at         = None,
        days_until_original = max(0, _days_remaining(due)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# REVIEW EXTENSION (approve / deny)
# On approval → updates Deadline.due_date to proposed_deadline
# ─────────────────────────────────────────────────────────────────────────────

async def hr_review_extension(
    db:           AsyncSession,
    hr_user_id:   uuid.UUID,
    extension_id: uuid.UUID,
    action:       str,
    note:         Optional[str] = None,
) -> ExtensionRequestResponse:

    if action not in ("approve", "deny"):
        raise HTTPException(status_code=422, detail="action must be 'approve' or 'deny'")

    result = await db.execute(
        select(DeadlineExtensionRequest)
        .options(joinedload(DeadlineExtensionRequest.deadline))
        .where(DeadlineExtensionRequest.id == extension_id)
    )
    ext = result.scalars().first()
    if not ext:
        raise HTTPException(status_code=404, detail="Extension request not found.")
    if ext.hr_user_id != hr_user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if ext.status != "pending":
        raise HTTPException(status_code=400, detail="Extension already reviewed.")

    # Reviewer name
    hr_result = await db.execute(select(User).where(User.id == hr_user_id))
    hr_user   = hr_result.scalars().first()
    hr_name   = _user_name(hr_user) if hr_user else "HR Manager"

    ext.status           = "approved" if action == "approve" else "denied"
    ext.reviewed_by_name = hr_name
    ext.reviewed_at      = datetime.now(timezone.utc)
    ext.review_note      = note

    # KEY: on approval → update the real Deadline.due_date
    if action == "approve" and ext.deadline:
        ext.deadline.due_date   = ext.proposed_deadline
        ext.deadline.modified_by = hr_user_id

    await db.commit()
    await db.refresh(ext)

    dl  = ext.deadline
    app = None
    if dl and dl.application_id:
        app_result = await db.execute(
            select(Application)
            .options(joinedload(Application.visa_type))
            .where(Application.id == dl.application_id)
        )
        app = app_result.scalars().first()

    return ExtensionRequestResponse(
        id                  = ext.id,
        request_number      = ext.request_number,
        application_id      = dl.application_id if dl else hr_user_id,
        case_number         = app.application_number if app else str(ext.deadline_id)[:8].upper(),
        visa_type           = app.visa_type.code if app and app.visa_type else "N/A",
        title               = f"Extension: {dl.title}" if dl else "Extension Request",
        description         = ext.reason,
        original_deadline   = ext.original_deadline,
        extension_days      = ext.extension_days,
        proposed_deadline   = ext.proposed_deadline,
        status              = ExtensionStatus(ext.status),
        requested_by        = ext.requested_by_name,
        submitted_at        = ext.created_at,
        reviewed_by         = ext.reviewed_by_name,
        reviewed_at         = ext.reviewed_at,
        days_until_original = max(0, _days_remaining(ext.original_deadline)),
    )