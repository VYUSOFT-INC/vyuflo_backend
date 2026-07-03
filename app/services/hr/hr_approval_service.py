# app/services/hr/hr_approval_service.py
#
# Business logic for HR Approval Queue.
#
# The approval queue = Documents where:
#   - document.application_id links to an Application
#   - application.assigned_hr_id == current HR user
#   - document.status IN ('uploaded', 'pending_review') — awaiting HR action
#
# Approving a document sets status = 'verified'
# Requesting edits sets status = 'rejected' with rejection_reason
# Both create a DocumentActivity record.

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import joinedload

from app.models.visamodels import (
    Application,
    Document,
    DocumentType,
    DocumentActivity,
    EmployerEmployee,
    VisaType,
    User,
)
from app.schemas.hr.hr_approval_schemas import (
    ApprovalItemResponse,
    ApprovalListResponse,
    ApprovalStatsResponse,
    ApprovalItemStatus,
    ApprovalItemPriority,
    ApprovalItemDocType,
    ApprovalExtractedFieldResponse,
    ApprovalCommentResponse,
    ApprovalRevisionResponse,
    ApprovalActionNoteResponse,
)
from app.services.employee.services import db_create, db_update

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
    return name if name else user.email or "Unknown"


def _relative_time(dt: datetime) -> str:
    now   = datetime.now(timezone.utc)
    dt    = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    delta = now - dt
    mins  = int(delta.total_seconds() // 60)
    if mins < 1:    return "just now"
    if mins < 60:   return f"{mins} minutes ago"
    hours = mins // 60
    if hours < 24:  return f"{hours} hours ago"
    days  = hours // 24
    if days == 1:   return "Yesterday"
    if days < 30:   return f"{days} days ago"
    return dt.strftime("%b %d, %Y")


# AFTER — handles both date and datetime safely
def _infer_priority(doc: Document, app: Application) -> ApprovalItemPriority:
    if app.status == "rfe_response":  return ApprovalItemPriority.critical
    if app.status == "action_needed": return ApprovalItemPriority.high

    if app.due_date:
        from datetime import date as date_type
        now = datetime.now(timezone.utc)

        # due_date can be a plain date OR a timezone-aware datetime depending on DB driver
        if isinstance(app.due_date, date_type) and not isinstance(app.due_date, datetime):
            # Plain date → convert to midnight UTC datetime
            due = datetime(
                app.due_date.year, app.due_date.month, app.due_date.day,
                tzinfo=timezone.utc
            )
        elif app.due_date.tzinfo is None:
            # Naive datetime → assume UTC
            due = app.due_date.replace(tzinfo=timezone.utc)
        else:
            due = app.due_date

        days = (due - now).days
        if days <= 7:  return ApprovalItemPriority.high
        if days <= 30: return ApprovalItemPriority.medium

    return ApprovalItemPriority.low


def _infer_doc_type(doc_type_name: Optional[str]) -> ApprovalItemDocType:
    if not doc_type_name:
        return ApprovalItemDocType.document
    name = doc_type_name.lower()
    if "letter" in name or "verification" in name or "support" in name:
        return ApprovalItemDocType.letter
    if "form" in name or "i-" in name or "i9" in name:
        return ApprovalItemDocType.form
    if "certificate" in name or "degree" in name or "diploma" in name:
        return ApprovalItemDocType.certificate
    return ApprovalItemDocType.document


def _infer_status(doc: Document) -> ApprovalItemStatus:
    if doc.status == "verified":  return ApprovalItemStatus.approved
    if doc.status == "rejected":  return ApprovalItemStatus.edits_requested
    return ApprovalItemStatus.pending


# ─────────────────────────────────────────────────────────────────────────────
# LIST APPROVAL QUEUE
# ─────────────────────────────────────────────────────────────────────────────

async def hr_list_approvals(
    db:           AsyncSession,
    hr_user_id:   uuid.UUID,
    status:       Optional[str] = None,    # 'pending' | 'edits_requested' | 'approved' | 'all'
    priority:     Optional[str] = None,
    doc_type:     Optional[str] = None,
    date_range:   Optional[str] = "7days",
) -> ApprovalListResponse:
    """
    Returns all documents pending HR review for the HR user's cases.
    Joins: Document → Application (assigned_hr_id check) → User (employee) → DocumentType
    """

    # Date range filter
    date_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    if date_range == "30days":  date_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    if date_range == "90days":  date_cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    # Build the status filter for the DB query
    db_statuses = ["uploaded", "pending_review", "rejected", "verified"]
    if status == "pending":         db_statuses = ["uploaded", "pending_review"]
    elif status == "edits_requested": db_statuses = ["rejected"]
    elif status == "approved":      db_statuses = ["verified"]

    stmt = (
        select(Document)
        .join(Application, Document.application_id == Application.id)
        .options(
            joinedload(Document.document_type),
        )
        .where(
            Application.assigned_hr_id == hr_user_id,
            Document.application_id.isnot(None),
            Document.status.in_(db_statuses),
            Document.created_at >= date_cutoff,
        )
        .order_by(Document.created_at.desc())
        .limit(100)
    )
    result   = await db.execute(stmt)
    documents = result.scalars().all()

    if not documents:
        return ApprovalListResponse(
            items=[],
            stats=ApprovalStatsResponse(pending=0, approved_today=0, edits_requested=0, avg_response_hours=0.0),
            total=0,
        )

    # Load application info in one query
    app_ids    = list({d.application_id for d in documents if d.application_id})
    app_result = await db.execute(
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(Application.id.in_(app_ids))
    )
    app_map = {a.id: a for a in app_result.scalars().all()}

    # Load employee names
    user_ids    = list({app_map[d.application_id].user_id for d in documents if d.application_id and d.application_id in app_map})
    user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    user_map    = {u.id: u for u in user_result.scalars().all()}

    # Load activity (comments / history) for all docs
    activity_result = await db.execute(
        select(DocumentActivity)
        .where(DocumentActivity.document_id.in_([d.id for d in documents]))
        .order_by(DocumentActivity.created_at.desc())
    )
    activity_list = activity_result.scalars().all()
    # Group by document_id
    activity_map: dict[uuid.UUID, list[DocumentActivity]] = {}
    for act in activity_list:
        activity_map.setdefault(act.document_id, []).append(act)

    items: list[ApprovalItemResponse] = []
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    for doc in documents:
        app = app_map.get(doc.application_id)
        if not app:
            continue

        emp = user_map.get(app.user_id)
        emp_name = _user_name(emp)

        doc_type_name = doc.document_type.name if doc.document_type else "Document"
        doc_cat       = doc.document_type.category if doc.document_type else None

        inferred_priority = _infer_priority(doc, app)
        inferred_doc_type = _infer_doc_type(doc_type_name)
        inferred_status   = _infer_status(doc)

        # Apply filters
        if priority and priority != "all" and inferred_priority != priority: continue
        if doc_type and doc_type != "all" and inferred_doc_type != doc_type: continue

        # Build description
        desc_map = {
            "passport":          "Passport biographical page uploaded for identity verification.",
            "employment_letter": "Employment verification letter confirming position and salary details.",
            "degree":            "Educational degree certificate for specialty occupation requirement.",
            "form_i129":         "Form I-129 petition for nonimmigrant worker.",
            "lca":               "Labor Condition Application approval notice from DOL.",
            "pay_stubs":         "Recent pay stubs confirming employment and compensation.",
        }
        doc_key   = doc.document_type.name.lower().replace(" ", "_").replace("-", "_") if doc.document_type else ""
        description = desc_map.get(doc_key) or f"{doc_type_name} document submitted for HR review."

        # Build action_note from rejection_reason (edits_requested case)
        action_note = None
        if doc.status == "rejected" and doc.rejection_reason:
            action_note = ApprovalActionNoteResponse(
                type  = "edit",
                title = "Edit Requested",
                body  = doc.rejection_reason,
            )

        # Build comments from DocumentActivity notes
        activities = activity_map.get(doc.id, [])
        comments: list[ApprovalCommentResponse] = []
        for act in activities[:3]:   # max 3 recent comments
            if act.note:
                comments.append(ApprovalCommentResponse(
                    author = "Team Member",
                    role   = act.actor_type.replace("_", " ").title() if act.actor_type else "User",
                    time   = _relative_time(act.created_at),
                    text   = act.note,
                ))

        # Build revisions from version history
        revisions: list[ApprovalRevisionResponse] = []
        if doc.version > 1:
            revisions.append(ApprovalRevisionResponse(
                version = f"v{doc.version}",
                label   = "Current Version",
                author  = emp_name,
                time    = _relative_time(doc.updated_at),
            ))
            revisions.append(ApprovalRevisionResponse(
                version = f"v{doc.version - 1}",
                label   = "Previous Version",
                author  = "AI-generated",
                time    = _relative_time(doc.created_at),
            ))

        items.append(ApprovalItemResponse(
            id            = doc.id,
            title         = doc_type_name,
            priority      = inferred_priority,
            doc_type      = inferred_doc_type,
            visa_type     = (
                f"{app.visa_type.name} ({app.visa_type.code})"
                if app.visa_type else "Immigration"
            ),
            employee_name = emp_name,
            case_number   = app.application_number or f"CASE-{str(app.id)[:8].upper()}",
            submitted_ago = _relative_time(doc.created_at),
            description   = description,
            status        = inferred_status,
            ai_confidence = doc.ocr_confidence or 0,
            ai_note       = (
                f"AI extracted {doc.ocr_confidence or 0}% confidence. "
                "Review key fields before approving."
                if doc.ocr_confidence else ""
            ),
            extracted_label  = "Key Information Extracted:" if doc.ocr_confidence else "",
            extracted_fields = [],    # OCR fields loaded separately from document_ocr_fields table
            action_note      = action_note,
            comments         = comments if comments else None,
            revisions        = revisions if revisions else None,
            comment_count    = len(comments) if comments else None,
        ))

    # ── Compute stats ─────────────────────────────────────────────────────────
    all_pending   = sum(1 for i in items if i.status == ApprovalItemStatus.pending)
    approved_today = sum(1 for d in documents if d.status == "verified" and d.verified_at and d.verified_at >= today_start)
    edits_req      = sum(1 for i in items if i.status == ApprovalItemStatus.edits_requested)

    # Average response time in hours (verified docs this period)
    verified_docs = [d for d in documents if d.status == "verified" and d.verified_at]
    if verified_docs:
        avg_hours = sum(
            (d.verified_at - d.created_at).total_seconds() / 3600
            for d in verified_docs
        ) / len(verified_docs)
    else:
        avg_hours = 0.0

    stats = ApprovalStatsResponse(
        pending             = all_pending,
        approved_today      = approved_today,
        edits_requested     = edits_req,
        avg_response_hours  = round(avg_hours, 1),
    )

    return ApprovalListResponse(items=items, stats=stats, total=len(items))


# ─────────────────────────────────────────────────────────────────────────────
# APPROVE (single)
# ─────────────────────────────────────────────────────────────────────────────

async def hr_approve_document(
    db:          AsyncSession,
    hr_user_id:  uuid.UUID,
    document_id: uuid.UUID,
    note:        Optional[str] = None,
) -> ApprovalItemResponse:
    result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Verify HR owns this case
    if doc.application_id:
        app_result = await db.execute(
            select(Application)
            .options(joinedload(Application.visa_type))
            .where(Application.id == doc.application_id)
        )
        app = app_result.scalars().first()
        if app and app.assigned_hr_id != hr_user_id:
            raise HTTPException(status_code=403, detail="Access denied.")
    else:
        app = None

    await db_update(db, Document, document_id, {
        "status":      "verified",
        "verified_by": hr_user_id,
        "verified_at": datetime.now(timezone.utc),
        "modified_by": hr_user_id,
    })

    activity = DocumentActivity(
        document_id = document_id,
        action      = "verified",
        actor_id    = hr_user_id,
        actor_type  = "hr_admin",
        note        = note,
        created_by  = hr_user_id,
    )
    await db_create(db, activity)

    # Reload
    result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.id == document_id)
    )
    doc = result.scalars().first()

    emp_name = "Employee"
    if app:
        emp_result = await db.execute(select(User).where(User.id == app.user_id))
        emp = emp_result.scalars().first()
        if emp: emp_name = _user_name(emp)

    return ApprovalItemResponse(
        id            = doc.id,
        title         = doc.document_type.name if doc.document_type else "Document",
        priority      = _infer_priority(doc, app) if app else ApprovalItemPriority.low,
        doc_type      = _infer_doc_type(doc.document_type.name if doc.document_type else None),
        visa_type     = app.visa_type.name if app and app.visa_type else "Immigration",
        employee_name = emp_name,
        case_number   = app.application_number if app else "N/A",
        submitted_ago = _relative_time(doc.created_at),
        description   = f"{doc.document_type.name if doc.document_type else 'Document'} has been approved.",
        status        = ApprovalItemStatus.approved,
        ai_confidence = doc.ocr_confidence or 0,
        ai_note       = "",
        extracted_label  = "",
        extracted_fields = [],
        action_note      = None,
        comments         = None,
        revisions        = None,
        comment_count    = None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST EDITS (single)
# ─────────────────────────────────────────────────────────────────────────────

async def hr_request_edits(
    db:          AsyncSession,
    hr_user_id:  uuid.UUID,
    document_id: uuid.UUID,
    note:        str,
) -> ApprovalItemResponse:
    if not note:
        raise HTTPException(status_code=422, detail="note is required for edit requests.")

    result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if doc.application_id:
        app_result = await db.execute(
            select(Application)
            .options(joinedload(Application.visa_type))
            .where(Application.id == doc.application_id)
        )
        app = app_result.scalars().first()
        if app and app.assigned_hr_id != hr_user_id:
            raise HTTPException(status_code=403, detail="Access denied.")
    else:
        app = None

    await db_update(db, Document, document_id, {
        "status":           "rejected",
        "rejection_reason": note,
        "modified_by":      hr_user_id,
    })

    activity = DocumentActivity(
        document_id = document_id,
        action      = "rejected",
        actor_id    = hr_user_id,
        actor_type  = "hr_admin",
        note        = f"Edit requested: {note}",
        created_by  = hr_user_id,
    )
    await db_create(db, activity)

    result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.id == document_id)
    )
    doc = result.scalars().first()

    emp_name = "Employee"
    if app:
        emp_result = await db.execute(select(User).where(User.id == app.user_id))
        emp = emp_result.scalars().first()
        if emp: emp_name = _user_name(emp)

    return ApprovalItemResponse(
        id            = doc.id,
        title         = doc.document_type.name if doc.document_type else "Document",
        priority      = _infer_priority(doc, app) if app else ApprovalItemPriority.low,
        doc_type      = _infer_doc_type(doc.document_type.name if doc.document_type else None),
        visa_type     = app.visa_type.name if app and app.visa_type else "Immigration",
        employee_name = emp_name,
        case_number   = app.application_number if app else "N/A",
        submitted_ago = _relative_time(doc.created_at),
        description   = f"Edits requested for {doc.document_type.name if doc.document_type else 'document'}.",
        status        = ApprovalItemStatus.edits_requested,
        ai_confidence = 0,
        ai_note       = "",
        extracted_label  = "",
        extracted_fields = [],
        action_note = ApprovalActionNoteResponse(
            type  = "edit",
            title = "Edit Requested",
            body  = note,
        ),
        comments      = None,
        revisions     = None,
        comment_count = None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# BULK APPROVE
# ─────────────────────────────────────────────────────────────────────────────

async def hr_bulk_approve(
    db:           AsyncSession,
    hr_user_id:   uuid.UUID,
    document_ids: list[uuid.UUID],
    note:         Optional[str] = None,
) -> dict:
    approved = failed = 0
    now      = datetime.now(timezone.utc)

    for doc_id in document_ids:
        try:
            result = await db.execute(
                select(Document)
                .join(Application, Document.application_id == Application.id)
                .where(
                    Document.id == doc_id,
                    Application.assigned_hr_id == hr_user_id,
                )
            )
            doc = result.scalars().first()
            if not doc:
                failed += 1
                continue

            await db_update(db, Document, doc_id, {
                "status":      "verified",
                "verified_by": hr_user_id,
                "verified_at": now,
                "modified_by": hr_user_id,
            })

            activity = DocumentActivity(
                document_id = doc_id,
                action      = "verified",
                actor_id    = hr_user_id,
                actor_type  = "hr_admin",
                note        = note or "Bulk approved",
                created_by  = hr_user_id,
            )
            await db_create(db, activity)
            approved += 1

        except Exception:
            failed += 1

    return {"approved": approved, "failed": failed}