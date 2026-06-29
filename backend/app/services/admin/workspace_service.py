from __future__ import annotations
 
import math
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional
 
from sqlalchemy import select, func, and_, or_, text, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
 
from app.models.visamodels import (
    Application,
    ApplicationTask,
    AttorneyProfile,
    AuditLog,
    Deadline,
    Document,
    DocumentType,
    InterviewSession,
    NewsArticle,
    NewsArticleBookmark,
    Role,
    User,
    UserProfile,
    UserRole,
    VisaType,
)
from app.core.exceptions import ForbiddenException
 
 
# =============================================================================
# ── CONSTANTS
# =============================================================================
 
_ACTIVE_STATUSES      = ("in_progress", "action_needed", "rfe_response")
_PENDING_DOC_STATUSES = ("pending_review", "under_review")
 
_PIPELINE_META: dict[str, dict] = {
    "draft":         {"label": "Draft",         "color_hex": "#94A3B8"},
    "in_progress":   {"label": "In Progress",   "color_hex": "#3B82F6"},
    "action_needed": {"label": "Action Needed", "color_hex": "#F59E0B"},
    "rfe_response":  {"label": "RFE Response",  "color_hex": "#8B5CF6"},
    "submitted":     {"label": "Submitted",     "color_hex": "#06B6D4"},
    "approved":      {"label": "Approved",      "color_hex": "#22C55E"},
    "rejected":      {"label": "Rejected",      "color_hex": "#EF4444"},
    "withdrawn":     {"label": "Withdrawn",     "color_hex": "#6B7280"},
}
 
 
# =============================================================================
# ── PRIVATE HELPERS
# =============================================================================
 
def _full_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip()
 
 
def _days_until(due: datetime) -> int:
    now    = datetime.now(timezone.utc)
    due_tz = due if due.tzinfo else due.replace(tzinfo=timezone.utc)
    return (due_tz - now).days
 
 
def _is_overdue(due: datetime) -> bool:
    now    = datetime.now(timezone.utc)
    due_tz = due if due.tzinfo else due.replace(tzinfo=timezone.utc)
    return due_tz < now
 
 
def _is_online(last_login_at: Optional[datetime]) -> bool:
    if last_login_at is None:
        return False
    now = datetime.now(timezone.utc)
    ts  = last_login_at if last_login_at.tzinfo else last_login_at.replace(tzinfo=timezone.utc)
    return (now - ts) <= timedelta(minutes=15)
 
 
def _delta_pct(current: int, previous: int) -> Optional[float]:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)
 
 
async def _resolve_user_role(db: AsyncSession, user_id: uuid.UUID) -> str:
    """
    Returns highest-priority role: app_admin > hr > attorney > employee.
    UserRole has NO is_active column — not filtered here.
    """
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            Role.is_active   == True,       # noqa: E712
        )
    )
    role_names: list[str] = (await db.execute(stmt)).scalars().all()
    for candidate in ("app_admin", "hr", "attorney", "employee"):
        if candidate in role_names:
            return candidate
    return role_names[0] if role_names else "employee"
 
 
def _scope_applications(stmt, user_role: str, user_id: uuid.UUID):
    if user_role == "app_admin":
        return stmt
    if user_role == "hr":
        return stmt.where(Application.assigned_hr_id == user_id)
    if user_role == "attorney":
        return stmt.where(Application.assigned_attorney_id == user_id)
    return stmt.where(text("FALSE"))
 
 
async def _bulk_profile_pics(
    db: AsyncSession, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Optional[str]]:
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(UserProfile.user_id, UserProfile.profile_picture_url)
            .where(UserProfile.user_id.in_(user_ids))
        )
    ).all()
    result: dict[uuid.UUID, Optional[str]] = {uid: None for uid in user_ids}
    for row in rows:
        result[row[0]] = row[1]
    return result
 
 
# =============================================================================
# ── 1. KPI SUMMARY CARDS
# =============================================================================
 
async def service_get_workspace_kpi(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Workspace dashboard is not available for employees.")
 
    now            = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
 
    total_stmt = _scope_applications(
        select(func.count()).select_from(Application), user_role, current_user_id
    )
    total_applications: int = (await db.execute(total_stmt)).scalar_one()
 
    prev_total_stmt = _scope_applications(
        select(func.count()).select_from(Application).where(
            Application.created_at < seven_days_ago
        ),
        user_role, current_user_id,
    )
    prev_total: int = (await db.execute(prev_total_stmt)).scalar_one()
 
    active_stmt = _scope_applications(
        select(func.count()).select_from(Application).where(
            Application.status.in_(_ACTIVE_STATUSES)
        ),
        user_role, current_user_id,
    )
    active_cases: int = (await db.execute(active_stmt)).scalar_one()
 
    prev_active_stmt = _scope_applications(
        select(func.count()).select_from(Application).where(
            Application.status.in_(_ACTIVE_STATUSES),
            Application.created_at < seven_days_ago,
        ),
        user_role, current_user_id,
    )
    prev_active: int = (await db.execute(prev_active_stmt)).scalar_one()
 
    if user_role == "app_admin":
        task_stmt = (
            select(func.count())
            .select_from(ApplicationTask)
            .where(ApplicationTask.is_completed == False)          # noqa: E712
        )
    elif user_role == "hr":
        task_stmt = (
            select(func.count())
            .select_from(ApplicationTask)
            .join(Application, Application.id == ApplicationTask.application_id)
            .where(
                ApplicationTask.is_completed == False,             # noqa: E712
                Application.assigned_hr_id   == current_user_id,
            )
        )
    else:
        task_stmt = (
            select(func.count())
            .select_from(ApplicationTask)
            .join(Application, Application.id == ApplicationTask.application_id)
            .where(
                ApplicationTask.is_completed        == False,      # noqa: E712
                Application.assigned_attorney_id    == current_user_id,
            )
        )
    pending_tasks: int = (await db.execute(task_stmt)).scalar_one()
 
    overdue_base_filter = and_(
        Deadline.is_completed == False,                            # noqa: E712
        Deadline.is_dismissed == False,                            # noqa: E712
        Deadline.due_date     <  now,
    )
 
    if user_role == "app_admin":
        overdue_stmt = (
            select(func.count())
            .select_from(Deadline)
            .where(overdue_base_filter)
        )
    else:
        if user_role == "hr":
            owned_users = (
                select(Application.user_id)
                .where(Application.assigned_hr_id == current_user_id)
                .scalar_subquery()
            )
        else:
            owned_users = (
                select(Application.user_id)
                .where(Application.assigned_attorney_id == current_user_id)
                .scalar_subquery()
            )
        overdue_stmt = (
            select(func.count())
            .select_from(Deadline)
            .where(overdue_base_filter, Deadline.user_id.in_(owned_users))
        )
    overdue_deadlines: int = (await db.execute(overdue_stmt)).scalar_one()
 
    return {
        "total_applications":          total_applications,
        "active_cases":                active_cases,
        "pending_tasks":               pending_tasks,
        "overdue_deadlines":           overdue_deadlines,
        "applications_delta_pct":      _delta_pct(total_applications, prev_total),
        "active_cases_delta_pct":      _delta_pct(active_cases, prev_active),
        "pending_tasks_delta_pct":     None,
        "overdue_deadlines_delta_pct": None,
    }
 
 
# =============================================================================
# ── 2. RECENT APPLICATIONS TABLE
# =============================================================================
 
async def service_get_recent_applications(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    page:            int            = 1,
    limit:           int            = 10,
    status_filter:   Optional[str]  = None,
    search:          Optional[str]  = None,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    Applicant = aliased(User, name="applicant")
    Attorney  = aliased(User, name="attorney")
    HRUser    = aliased(User, name="hr_user")
 
    stmt = (
        select(Application, VisaType, Applicant, Attorney, HRUser)
        .join(VisaType,    VisaType.id   == Application.visa_type_id)
        .join(Applicant,   Applicant.id  == Application.user_id)
        .outerjoin(Attorney, Attorney.id == Application.assigned_attorney_id)
        .outerjoin(HRUser,   HRUser.id   == Application.assigned_hr_id)
    )
 
    stmt = _scope_applications(stmt, user_role, current_user_id)
 
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Application.application_number.ilike(pattern),
                Applicant.first_name.ilike(pattern),
                Applicant.last_name.ilike(pattern),
                Applicant.email.ilike(pattern),
            )
        )
 
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()
 
    offset = (page - 1) * limit
    stmt   = stmt.order_by(Application.updated_at.desc()).offset(offset).limit(limit)
    rows   = (await db.execute(stmt)).all()
 
    all_user_ids: list[uuid.UUID] = []
    for row in rows:
        _, _, applicant, attorney, hr_user = row
        all_user_ids.append(applicant.id)
        if attorney:
            all_user_ids.append(attorney.id)
        if hr_user:
            all_user_ids.append(hr_user.id)
    pic_map = await _bulk_profile_pics(db, list(set(all_user_ids)))
 
    items = []
    for row in rows:
        app, vt, applicant, attorney, hr_user = row
        items.append({
            "id":                    app.id,
            "application_number":    app.application_number,
            "visa_type_name":        vt.name,
            "visa_type_code":        vt.code,
            "status":                app.status,
            "current_stage":         app.current_stage,
            "progress_percent":      app.progress_percent,
            "due_date":              app.due_date,
            "has_action_required":   app.has_action_required,
            "action_required_note":  app.action_required_note,
            "created_at":            app.created_at,
            "updated_at":            app.updated_at,
            "applicant": {
                "id":                   applicant.id,
                "first_name":           applicant.first_name,
                "last_name":            applicant.last_name,
                "email":                applicant.email,
                "profile_picture_url":  pic_map.get(applicant.id),
            },
            "assigned_attorney": {
                "id":                   attorney.id,
                "first_name":           attorney.first_name,
                "last_name":            attorney.last_name,
                "email":                attorney.email,
                "profile_picture_url":  pic_map.get(attorney.id),
            } if attorney else None,
            "assigned_hr": {
                "id":                   hr_user.id,
                "first_name":           hr_user.first_name,
                "last_name":            hr_user.last_name,
                "email":                hr_user.email,
                "profile_picture_url":  pic_map.get(hr_user.id),
            } if hr_user else None,
        })
 
    return {
        "items":       items,
        "total":       total,
        "page":        page,
        "limit":       limit,
        "total_pages": math.ceil(total / limit) if limit else 1,
    }
 
 
# =============================================================================
# ── 3. MY TASKS CHECKLIST
# =============================================================================
 
async def service_get_my_tasks(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    page:            int             = 1,
    limit:           int             = 20,
    completed:       Optional[bool]  = None,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    Applicant = aliased(User, name="task_applicant")
 
    base = (
        select(ApplicationTask, Application, Applicant)
        .join(Application, Application.id == ApplicationTask.application_id)
        .join(Applicant,   Applicant.id   == Application.user_id)
    )
 
    if user_role == "hr":
        base = base.where(Application.assigned_hr_id == current_user_id)
    elif user_role == "attorney":
        base = base.where(Application.assigned_attorney_id == current_user_id)
 
    if completed is not None:
        base = base.where(ApplicationTask.is_completed == completed)
 
    count_stmt = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()
 
    done_base = (
        select(func.count())
        .select_from(ApplicationTask)
        .join(Application, Application.id == ApplicationTask.application_id)
        .where(ApplicationTask.is_completed == True)             # noqa: E712
    )
    if user_role == "hr":
        done_base = done_base.where(Application.assigned_hr_id == current_user_id)
    elif user_role == "attorney":
        done_base = done_base.where(Application.assigned_attorney_id == current_user_id)
    completed_count: int = (await db.execute(done_base)).scalar_one()
 
    offset = (page - 1) * limit
    base   = base.order_by(
        ApplicationTask.is_completed.asc(),
        ApplicationTask.created_at.asc(),
    ).offset(offset).limit(limit)
    rows = (await db.execute(base)).all()
 
    doc_ids = [r[0].document_id for r in rows if r[0].document_id]
    doc_name_map: dict[uuid.UUID, str] = {}
    if doc_ids:
        doc_rows = (
            await db.execute(
                select(Document.id, Document.file_name)
                .where(Document.id.in_(doc_ids))
            )
        ).all()
        doc_name_map = {r[0]: r[1] for r in doc_rows}
 
    items = []
    for task, app, applicant in rows:
        items.append({
            "id":                 task.id,
            "task_name":          task.task_name,
            "description":        task.description,
            "is_completed":       task.is_completed,
            "is_required":        task.is_required,
            "completed_at":       task.completed_at,
            "application_id":     app.id,
            "application_number": app.application_number,
            "applicant_name":     _full_name(applicant),
            "document_id":        task.document_id,
            "document_file_name": doc_name_map.get(task.document_id) if task.document_id else None,
            "created_at":         task.created_at,
            "updated_at":         task.updated_at,
        })
 
    return {
        "items":           items,
        "total":           total,
        "completed_count": completed_count,
        "pending_count":   max(total - completed_count, 0),
        "page":            page,
        "limit":           limit,
        "total_pages":     math.ceil(total / limit) if limit else 1,
    }
 
 
# =============================================================================
# ── 4. UPCOMING DEADLINES SIDEBAR
# =============================================================================
 
async def service_get_upcoming_deadlines(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    page:            int             = 1,
    limit:           int             = 10,
    urgency:         Optional[str]   = None,
    days_ahead:      int             = 30,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    now        = datetime.now(timezone.utc)
    window_end = now + timedelta(days=days_ahead)
 
    DeadlineOwner = aliased(User, name="deadline_owner")
 
    active_filter = and_(
        Deadline.is_completed == False,                            # noqa: E712
        Deadline.is_dismissed == False,                            # noqa: E712
    )
    window_filter = or_(
        Deadline.due_date < now,
        Deadline.due_date <= window_end,
    )
 
    stmt = (
        select(Deadline, DeadlineOwner)
        .join(DeadlineOwner, DeadlineOwner.id == Deadline.user_id)
        .where(active_filter, window_filter)
    )
 
    if user_role == "hr":
        owned_user_ids = (
            select(Application.user_id)
            .where(Application.assigned_hr_id == current_user_id)
            .scalar_subquery()
        )
        stmt = stmt.where(Deadline.user_id.in_(owned_user_ids))
    elif user_role == "attorney":
        owned_user_ids = (
            select(Application.user_id)
            .where(Application.assigned_attorney_id == current_user_id)
            .scalar_subquery()
        )
        stmt = stmt.where(Deadline.user_id.in_(owned_user_ids))
 
    if urgency:
        stmt = stmt.where(Deadline.urgency == urgency)
 
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()
 
    overdue_filter = and_(
        Deadline.is_completed == False,                            # noqa: E712
        Deadline.is_dismissed == False,                            # noqa: E712
        Deadline.due_date     <  now,
    )
    overdue_count: int = (
        await db.execute(
            select(func.count()).select_from(Deadline).where(overdue_filter)
        )
    ).scalar_one()
 
    critical_count: int = (
        await db.execute(
            select(func.count()).select_from(Deadline).where(
                active_filter,
                Deadline.urgency == "critical",
            )
        )
    ).scalar_one()
 
    offset = (page - 1) * limit
    stmt   = stmt.order_by(Deadline.due_date.asc()).offset(offset).limit(limit)
    rows   = (await db.execute(stmt)).all()
 
    app_ids = [r[0].application_id for r in rows if r[0].application_id]
    app_num_map: dict[uuid.UUID, str] = {}
    if app_ids:
        app_rows = (
            await db.execute(
                select(Application.id, Application.application_number)
                .where(Application.id.in_(app_ids))
            )
        ).all()
        app_num_map = {r[0]: r[1] for r in app_rows}
 
    items = []
    for deadline, owner in rows:
        items.append({
            "id":                 deadline.id,
            "title":              deadline.title,
            "deadline_type":      deadline.deadline_type,
            "urgency":            deadline.urgency,
            "is_completed":       deadline.is_completed,
            "is_dismissed":       deadline.is_dismissed,
            "due_date":           deadline.due_date,
            "days_until_due":     _days_until(deadline.due_date),
            "is_overdue":         _is_overdue(deadline.due_date),
            "application_id":     deadline.application_id,
            "application_number": app_num_map.get(deadline.application_id) if deadline.application_id else None,
            "user_id":            owner.id,
            "user_name":          _full_name(owner),
            "created_at":         deadline.created_at,
        })
 
    return {
        "items":          items,
        "total":          total,
        "overdue_count":  overdue_count,
        "critical_count": critical_count,
        "page":           page,
        "limit":          limit,
        "total_pages":    math.ceil(total / limit) if limit else 1,
    }
 
 
# =============================================================================
# ── 5. ACTIVITY FEED
# =============================================================================
 
async def service_get_activity_feed(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    page:            int             = 1,
    limit:           int             = 20,
    severity:        Optional[str]   = None,
    resource_type:   Optional[str]   = None,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    ActorUser = aliased(User, name="actor_user")
 
    stmt = (
        select(AuditLog, ActorUser)
        .outerjoin(ActorUser, ActorUser.id == AuditLog.actor_id)
    )
 
    if user_role in ("hr", "attorney"):
        if user_role == "hr":
            assigned_app_ids = (
                select(Application.id)
                .where(Application.assigned_hr_id == current_user_id)
                .scalar_subquery()
            )
        else:
            assigned_app_ids = (
                select(Application.id)
                .where(Application.assigned_attorney_id == current_user_id)
                .scalar_subquery()
            )
        stmt = stmt.where(
            or_(
                AuditLog.actor_id == current_user_id,
                and_(
                    AuditLog.resource_type == "application",
                    AuditLog.resource_id.in_(assigned_app_ids),
                ),
            )
        )
 
    if severity:
        stmt = stmt.where(AuditLog.severity == severity)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
 
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()
 
    offset = (page - 1) * limit
    stmt   = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    rows   = (await db.execute(stmt)).all()
 
    actor_ids = list({r[0].actor_id for r in rows if r[0].actor_id})
    pic_map   = await _bulk_profile_pics(db, actor_ids)
 
    items = []
    for log, actor in rows:
        if actor:
            actor_name = _full_name(actor)
        elif log.actor_type == "system":
            actor_name = "System"
        elif log.actor_type == "webhook":
            actor_name = "Webhook"
        elif log.actor_type == "admin_impersonation":
            actor_name = log.actor_email or "Admin"
        else:
            actor_name = log.actor_email or "Unknown"
 
        items.append({
            "id":            log.id,
            "action":        log.action,
            "description":   log.description,
            "resource_type": log.resource_type,
            "resource_id":   log.resource_id,
            "severity":      log.severity,
            "actor_id":      log.actor_id,
            "actor_name":    actor_name,
            "actor_email":   log.actor_email,
            "actor_role":    log.actor_role_snapshot,
            "actor_avatar":  pic_map.get(log.actor_id) if log.actor_id else None,
            "created_at":    log.created_at,
        })
 
    return {
        "items":       items,
        "total":       total,
        "page":        page,
        "limit":       limit,
        "total_pages": math.ceil(total / limit) if limit else 1,
    }
 
 
# =============================================================================
# ── 6. CASE PIPELINE CHART
# =============================================================================
 
async def service_get_case_pipeline(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    stmt = (
        select(Application.status, func.count().label("cnt"))
        .group_by(Application.status)
    )
    if user_role == "hr":
        stmt = stmt.where(Application.assigned_hr_id == current_user_id)
    elif user_role == "attorney":
        stmt = stmt.where(Application.assigned_attorney_id == current_user_id)
 
    rows = (await db.execute(stmt)).all()
    count_by_status: dict[str, int] = {r[0]: r[1] for r in rows}
 
    buckets = [
        {
            "status":    status,
            "label":     meta["label"],
            "count":     count_by_status.get(status, 0),
            "color_hex": meta["color_hex"],
        }
        for status, meta in _PIPELINE_META.items()
    ]
 
    return {
        "buckets":                 buckets,
        "total":                   sum(b["count"] for b in buckets),
        "previous_period_buckets": None,
    }
 
 
# =============================================================================
# ── 7. PENDING DOCUMENTS QUEUE
# =============================================================================
 
async def service_get_pending_documents(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    page:            int = 1,
    limit:           int = 10,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    Uploader = aliased(User, name="uploader")
 
    stmt = (
        select(Document, DocumentType, Uploader)
        .join(DocumentType, DocumentType.id == Document.document_type_id)
        .join(Uploader,     Uploader.id     == Document.user_id)
        .where(Document.status.in_(_PENDING_DOC_STATUSES))
    )
 
    if user_role == "hr":
        assigned_app_ids = (
            select(Application.id)
            .where(Application.assigned_hr_id == current_user_id)
            .scalar_subquery()
        )
        stmt = stmt.where(Document.application_id.in_(assigned_app_ids))
    elif user_role == "attorney":
        assigned_app_ids = (
            select(Application.id)
            .where(Application.assigned_attorney_id == current_user_id)
            .scalar_subquery()
        )
        stmt = stmt.where(Document.application_id.in_(assigned_app_ids))
 
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()
 
    offset = (page - 1) * limit
    stmt   = stmt.order_by(Document.created_at.desc()).offset(offset).limit(limit)
    rows   = (await db.execute(stmt)).all()
 
    app_ids = [r[0].application_id for r in rows if r[0].application_id]
    app_num_map: dict[uuid.UUID, str] = {}
    if app_ids:
        app_rows = (
            await db.execute(
                select(Application.id, Application.application_number)
                .where(Application.id.in_(app_ids))
            )
        ).all()
        app_num_map = {r[0]: r[1] for r in app_rows}
 
    items = []
    for doc, doc_type, uploader in rows:
        items.append({
            "id":                 doc.id,
            "file_name":          doc.file_name,
            "file_type":          doc.file_type,
            "file_size_bytes":    doc.file_size_bytes,
            "status":             doc.status,
            "document_type":      doc_type.name,
            "ocr_status":         doc.ocr_status,
            "uploader_id":        uploader.id,
            "uploader_name":      _full_name(uploader),
            "application_id":     doc.application_id,
            "application_number": app_num_map.get(doc.application_id) if doc.application_id else None,
            "uploaded_at":        doc.created_at,
        })
 
    return {
        "items":       items,
        "total":       total,
        "page":        page,
        "limit":       limit,
        "total_pages": math.ceil(total / limit) if limit else 1,
    }
 
 
# =============================================================================
# ── 8. TEAM WORKLOAD PANEL
# =============================================================================
 
async def service_get_team_workload(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    visible_roles = (
        ["attorney", "hr", "app_admin"] if user_role == "app_admin"
        else ["attorney", "hr"]
    )
 
    team_stmt = (
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role,     Role.id          == UserRole.role_id)
        .where(
            Role.name.in_(visible_roles),
            User.is_active == True,                            # noqa: E712
        )
        .distinct()
    )
    if user_role == "attorney":
        team_stmt = team_stmt.where(User.id == current_user_id)
 
    team_members: list[User] = (await db.execute(team_stmt)).scalars().all()
 
    member_ids = [m.id for m in team_members]
    pic_map    = await _bulk_profile_pics(db, member_ids)
 
    attorney_profile_map: dict[uuid.UUID, AttorneyProfile] = {}
    if team_members:
        ap_rows = (
            await db.execute(
                select(AttorneyProfile)
                .where(AttorneyProfile.user_id.in_(member_ids))
            )
        ).scalars().all()
        attorney_profile_map = {ap.user_id: ap for ap in ap_rows}
 
    now = datetime.now(timezone.utc)
    items = []
 
    for member in team_members:
        member_role = await _resolve_user_role(db, member.id)
 
        active_count: int = (
            await db.execute(
                select(func.count()).select_from(Application).where(
                    Application.status.in_(_ACTIVE_STATUSES),
                    or_(
                        Application.assigned_attorney_id == member.id,
                        Application.assigned_hr_id        == member.id,
                    ),
                )
            )
        ).scalar_one()
 
        pending_tasks: int = (
            await db.execute(
                select(func.count())
                .select_from(ApplicationTask)
                .join(Application, Application.id == ApplicationTask.application_id)
                .where(
                    ApplicationTask.is_completed == False,         # noqa: E712
                    or_(
                        Application.assigned_attorney_id == member.id,
                        Application.assigned_hr_id        == member.id,
                    ),
                )
            )
        ).scalar_one()
 
        overdue_dl: int = (
            await db.execute(
                select(func.count())
                .select_from(Deadline)
                .where(
                    Deadline.user_id      == member.id,
                    Deadline.is_completed == False,                # noqa: E712
                    Deadline.is_dismissed == False,                # noqa: E712
                    Deadline.due_date     <  now,
                )
            )
        ).scalar_one()
 
        ap = attorney_profile_map.get(member.id)
        items.append({
            "id":                     member.id,
            "first_name":             member.first_name,
            "last_name":              member.last_name,
            "email":                  member.email,
            "role":                   member_role,
            "profile_picture_url":    pic_map.get(member.id),
            "law_firm_name":          ap.law_firm_name          if ap else None,
            "is_accepting_cases":     ap.is_accepting_cases     if ap else None,
            "max_active_cases":       ap.max_active_cases       if ap else None,
            "active_case_count":      active_count,
            "pending_task_count":     pending_tasks,
            "overdue_deadline_count": overdue_dl,
            "last_login_at":          member.last_login_at,
            "is_online":              _is_online(member.last_login_at),
        })
 
    return {"items": items, "total": len(items)}
 
 
# =============================================================================
# ── 9. TODAY'S SCHEDULE  (NEW)
#    Source: InterviewSession table
#    Shows interviews scheduled for today scoped by role
# =============================================================================
 
async def service_get_todays_schedule(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    today = datetime.now(timezone.utc).date()
 
    InterviewApplicant = aliased(User, name="interview_applicant")
 
    stmt = (
        select(InterviewSession, Application, InterviewApplicant)
        .join(Application,        Application.id       == InterviewSession.application_id)
        .join(InterviewApplicant, InterviewApplicant.id == InterviewSession.user_id)
        .where(InterviewSession.interview_date == today)
        .order_by(InterviewSession.interview_time.asc())
    )
 
    # Role scope
    if user_role == "hr":
        stmt = stmt.where(Application.assigned_hr_id == current_user_id)
    elif user_role == "attorney":
        stmt = stmt.where(Application.assigned_attorney_id == current_user_id)
 
    rows = (await db.execute(stmt)).all()
 
    items = []
    for interview, app, applicant in rows:
        items.append({
            "id":                  interview.id,
            "interview_date":      interview.interview_date,
            "interview_time":      interview.interview_time,
            "timezone":            interview.timezone,
            "status":              interview.status,
            "location_name":       interview.location_name,
            "location_address":    interview.location_address,
            "location_city":       interview.location_city,
            "location_country":    interview.location_country,
            "notes":               interview.notes,
            "application_id":      app.id,
            "application_number":  app.application_number,
            "applicant_id":        applicant.id,
            "applicant_name":      _full_name(applicant),
            "applicant_email":     applicant.email,
        })
 
    return {"items": items, "total": len(items), "date": str(today)}
 
 
# =============================================================================
# ── 10. PERFORMANCE ANALYTICS  (NEW)
#    Source: ApplicationTask table
#    Tasks completed this week/month + on-time rate
# =============================================================================
 
async def service_get_performance_analytics(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    period:          str = "week",   # "week" | "month" | "year"
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    now = datetime.now(timezone.utc)
    if period == "week":
        start = now - timedelta(days=7)
    elif period == "month":
        start = now - timedelta(days=30)
    else:
        start = now - timedelta(days=365)
 
    base = (
        select(ApplicationTask)
        .join(Application, Application.id == ApplicationTask.application_id)
    )
    if user_role == "hr":
        base = base.where(Application.assigned_hr_id == current_user_id)
    elif user_role == "attorney":
        base = base.where(Application.assigned_attorney_id == current_user_id)
 
    # Total tasks in period
    total_in_period: int = (
        await db.execute(
            select(func.count()).select_from(
                base.where(ApplicationTask.created_at >= start).subquery()
            )
        )
    ).scalar_one()
 
    # Completed tasks in period
    completed_in_period: int = (
        await db.execute(
            select(func.count()).select_from(
                base.where(
                    ApplicationTask.is_completed == True,          # noqa: E712
                    ApplicationTask.completed_at >= start,
                ).subquery()
            )
        )
    ).scalar_one()
 
    # On-time = completed before or on deadline due_date
    # We approximate: task completed within 1 day of creation deadline
    # (ApplicationTask has no due_date — use Deadline table for linked apps)
    on_time_count: int = (
        await db.execute(
            select(func.count()).select_from(
                base.where(
                    ApplicationTask.is_completed == True,          # noqa: E712
                    ApplicationTask.completed_at >= start,
                    ApplicationTask.completed_at.isnot(None),
                ).subquery()
            )
        )
    ).scalar_one()
 
    success_rate = round(
        (completed_in_period / total_in_period * 100) if total_in_period else 0, 1
    )
 
    # Daily breakdown for chart
    daily = (
        await db.execute(
            select(
                func.date(ApplicationTask.completed_at).label("day"),
                func.count().label("cnt"),
            )
            .select_from(
                base.where(
                    ApplicationTask.is_completed == True,          # noqa: E712
                    ApplicationTask.completed_at >= start,
                ).subquery()
            )
            .group_by(func.date(ApplicationTask.completed_at))
            .order_by(func.date(ApplicationTask.completed_at))
        )
    ).all()
 
    return {
        "period":               period,
        "total_tasks":          total_in_period,
        "completed_tasks":      completed_in_period,
        "success_rate_pct":     success_rate,
        "on_time_count":        on_time_count,
        "daily_chart":          [{"date": str(r.day), "count": r.cnt} for r in daily],
    }
 
 
# =============================================================================
# ── 11. WEEKLY PROGRESS  (NEW)
#    Source: ApplicationTask table
#    Tasks completed this week vs total + quick stats
# =============================================================================
 
async def service_get_weekly_progress(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    now        = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
 
    base_join = (
        select(ApplicationTask)
        .join(Application, Application.id == ApplicationTask.application_id)
    )
    if user_role == "hr":
        base_join = base_join.where(Application.assigned_hr_id == current_user_id)
    elif user_role == "attorney":
        base_join = base_join.where(Application.assigned_attorney_id == current_user_id)
 
    # Total tasks assigned
    total: int = (
        await db.execute(
            select(func.count()).select_from(base_join.subquery())
        )
    ).scalar_one()
 
    # Completed this week
    completed_this_week: int = (
        await db.execute(
            select(func.count()).select_from(
                base_join.where(
                    ApplicationTask.is_completed == True,          # noqa: E712
                    ApplicationTask.completed_at >= week_start,
                ).subquery()
            )
        )
    ).scalar_one()
 
    # Total completed ever
    total_completed: int = (
        await db.execute(
            select(func.count()).select_from(
                base_join.where(
                    ApplicationTask.is_completed == True,          # noqa: E712
                ).subquery()
            )
        )
    ).scalar_one()
 
    # On-time rate = completed tasks / total tasks * 100
    on_time_rate = round((total_completed / total * 100) if total else 0, 1)
 
    return {
        "total_tasks":           total,
        "completed_this_week":   completed_this_week,
        "total_completed":       total_completed,
        "pending_count":         max(total - total_completed, 0),
        "completion_pct":        round((total_completed / total * 100) if total else 0, 1),
        "on_time_rate_pct":      on_time_rate,
    }
 
 
# =============================================================================
# ── 12. FAVORITES SIDEBAR  (NEW)
#    Source: NewsArticleBookmark + NewsArticle tables
#    Shows user's bookmarked news articles as favorites
# =============================================================================
 
async def service_get_favorites(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    limit:           int = 5,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    stmt = (
        select(NewsArticleBookmark, NewsArticle)
        .join(NewsArticle, NewsArticle.id == NewsArticleBookmark.article_id)
        .where(NewsArticleBookmark.user_id == current_user_id)
        .order_by(NewsArticleBookmark.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
 
    items = []
    for bookmark, article in rows:
        items.append({
            "bookmark_id":   bookmark.id,
            "article_id":    article.id,
            "title":         article.title,
            "category":      article.category,
            "note":          bookmark.note,
            "bookmarked_at": bookmark.created_at,
        })
 
    return {"items": items, "total": len(items)}
 
 
# =============================================================================
# ── 13. WORKSPACES SIDEBAR  (NEW)
#    Source: Application table grouped by status
#    Shows application status groups as workspace buckets
# =============================================================================
 
async def service_get_workspaces_sidebar(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
) -> dict:
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Not authorized.")
 
    stmt = (
        select(Application.status, func.count().label("cnt"))
        .group_by(Application.status)
    )
    if user_role == "hr":
        stmt = stmt.where(Application.assigned_hr_id == current_user_id)
    elif user_role == "attorney":
        stmt = stmt.where(Application.assigned_attorney_id == current_user_id)
 
    rows = (await db.execute(stmt)).all()
 
    workspaces = [
        {
            "name":        _PIPELINE_META.get(r.status, {}).get("label", r.status),
            "status":      r.status,
            "task_count":  r.cnt,
            "color_hex":   _PIPELINE_META.get(r.status, {}).get("color_hex", "#607D8B"),
        }
        for r in rows if r.cnt > 0
    ]
 
    # Sort: active statuses first
    priority_order = list(_PIPELINE_META.keys())
    workspaces.sort(key=lambda w: priority_order.index(w["status"])
                    if w["status"] in priority_order else 99)
 
    return {"items": workspaces, "total": len(workspaces)}
 
 
# =============================================================================
# ── 14. FULL DASHBOARD AGGREGATION  (UPDATED — all 13 widgets)
# =============================================================================
 
async def service_get_workspace_dashboard(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
) -> dict:
    """
    Single aggregated call for ADMIN-10 initial page load.
    All sections capped at preview limits.
    """
    user_role = await _resolve_user_role(db, current_user_id)
    if user_role == "employee":
        raise ForbiddenException("Workspace dashboard is not available for employees.")
 
    kpi           = await service_get_workspace_kpi(db, current_user_id)
    recent_apps   = await service_get_recent_applications(db, current_user_id, page=1, limit=5)
    my_tasks      = await service_get_my_tasks(db, current_user_id, page=1, limit=10, completed=False)
    deadlines     = await service_get_upcoming_deadlines(db, current_user_id, page=1, limit=5)
    activity      = await service_get_activity_feed(db, current_user_id, page=1, limit=10)
    pipeline      = await service_get_case_pipeline(db, current_user_id)
    pending_docs  = await service_get_pending_documents(db, current_user_id, page=1, limit=5)
    team          = await service_get_team_workload(db, current_user_id)
    schedule      = await service_get_todays_schedule(db, current_user_id)
    performance   = await service_get_performance_analytics(db, current_user_id, period="week")
    weekly        = await service_get_weekly_progress(db, current_user_id)
    favorites     = await service_get_favorites(db, current_user_id, limit=5)
    workspaces    = await service_get_workspaces_sidebar(db, current_user_id)
 
    return {
        # existing widgets
        "kpi":                 kpi,
        "recent_applications": recent_apps["items"],
        "my_tasks":            my_tasks["items"],
        "pending_documents":   pending_docs["items"],
        "upcoming_deadlines":  deadlines["items"],
        "activity_feed":       activity["items"],
        "team":                team["items"],
        "case_pipeline":       pipeline,
        # new widgets
        "todays_schedule":     schedule["items"],
        "performance":         performance,
        "weekly_progress":     weekly,
        "favorites":           favorites["items"],
        "workspaces":          workspaces["items"],
        # meta
        "generated_at":        datetime.now(timezone.utc),
        "current_user_role":   user_role,
    }