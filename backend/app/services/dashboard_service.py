# app/services/dashboard_service.py
#
# Assembles the full employee dashboard payload.
# Replaces the original service with queries for:
#   case pipeline, action items, documents list, deadlines,
#   payments, case team, activity, and readiness.

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.visamodels import (
    Application,
    ApplicationStatusHistory,
    Document,
    DocumentActivity,
    User,
    UserProfile,
    UserVisaTarget,
    VisaType,
)
from app.schemas.employee.dashboard import (
    ActionItem,
    ActivityItemV2,
    CaseStage,
    CaseSummary,
    CaseTeamMember,
    DashboardResponse,
    DashboardStats,
    Deadline,
    DocumentSummaryItem,
    PaymentSummary,
    ReadinessSection,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Ordered pipeline stages — key, label, progress%
PIPELINE_STAGES: list[tuple[str, str, int]] = [
    ("profile_eligibility", "Profile & Eligibility",  10),
    ("document_collection", "Document Collection",     25),
    ("lca_filing",          "LCA Filing",              40),
    ("petition_prep",       "Petition Preparation",    55),
    ("uscis_filing",        "USCIS Filing",            70),
    ("uscis_review",        "USCIS Review",            85),
    ("decision",            "Decision",               100),
]

STAGE_KEY_TO_IDX = {key: i for i, (key, _, _) in enumerate(PIPELINE_STAGES)}

# Map Document.document_type → frontend category
DOC_CATEGORY_MAP: dict[str, str] = {
    "passport":          "Identity",
    "passport_photo":    "Identity",
    "visa_stamp":        "Identity",
    "i94":               "Identity",
    "degree":            "Education",
    "transcript":        "Education",
    "degree_evaluation": "Education",
    "resume":            "Employment",
    "offer_letter":      "Employment",
    "pay_stub":          "Employment",
    "support_letter":    "Petition",
    "lca_copy":          "Petition",
    "i129_draft":        "Petition",
}

# Map Document.status → frontend status string
DOC_STATUS_MAP: dict[str, str] = {
    "verified":       "verified",
    "pending_review": "pending_review",
    "rejected":       "action_required",    # rejected = employee needs to re-upload
    "uploaded":       "pending_review",      # uploaded but not yet reviewed
}

# Map DocumentActivity.action → ActivityItemV2.type
ACTIVITY_TYPE_MAP: dict[str, str] = {
    "uploaded":        "document_uploaded",
    "verified":        "document_verified",
    "rejected":        "document_rejected",
    "status_changed":  "stage_advanced",
    "version_updated": "document_uploaded",
    "ocr_completed":   "document_verified",
    "downloaded":      "document_uploaded",
    "viewed":          "case_note",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str:
    if dt is None:
        return _now().isoformat()
    return dt.isoformat() if dt.tzinfo else dt.replace(tzinfo=timezone.utc).isoformat()


def _days_between(target: datetime, ref: datetime | None = None) -> int:
    ref = ref or _now()
    # Ensure both are offset-aware
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    return (target - ref).days


def _deadline_urgency(days_left: int) -> str:
    if days_left < 0:
        return "overdue"
    if days_left <= 7:
        return "critical"
    if days_left <= 21:
        return "soon"
    return "normal"


def _action_priority(days_left: int | None) -> str:
    if days_left is None:
        return "medium"
    if days_left <= 5:
        return "urgent"
    if days_left <= 10:
        return "high"
    if days_left <= 21:
        return "medium"
    return "low"


def _doc_display_name(doc) -> str:
    """Human-readable name from the DocumentType relationship or file_name."""
    if doc.file_name:
        return doc.file_name
    if doc.document_type and doc.document_type.name:
        return doc.document_type.name.replace("_", " ").title()
    return "Document"


def _doc_category(doc) -> str:
    """Category from the eagerly-loaded DocumentType relationship."""
    if doc.document_type and doc.document_type.category:
        return doc.document_type.category.title()
    return "General"


def _doc_status(doc) -> str:
    """Map Document.status → frontend status string."""
    return DOC_STATUS_MAP.get(doc.status or "", "not_uploaded")


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE READINESS
# ─────────────────────────────────────────────────────────────────────────────

def _build_readiness(profile) -> tuple[int, list[ReadinessSection]]:
    """
    Returns (percentage, sections list).
    Checks real UserProfile fields — extend as you add more profile fields.
    """
    sections: list[ReadinessSection] = []

    # Personal Info — full_legal_name + nationality
    personal_done = bool(
        profile and profile.full_legal_name and profile.nationality
    )
    sections.append(ReadinessSection(
        key="personal_info", label="Personal Information",
        completed=personal_done, required=True,
    ))

    # Passport & ID — date_of_birth as proxy (passport upload checked separately)
    passport_done = bool(profile and profile.date_of_birth)
    sections.append(ReadinessSection(
        key="passport", label="Passport & ID",
        completed=passport_done, required=True,
    ))

    # Education History — check if education-related fields exist
    # TODO: replace with actual education model check once built
    education_done = False
    sections.append(ReadinessSection(
        key="education", label="Education History",
        completed=education_done, required=True,
    ))

    # Employment History — check if user has at least one employment doc
    # We'll set this from the caller if employment docs exist
    employment_done = bool(profile and profile.full_legal_name)  # placeholder
    sections.append(ReadinessSection(
        key="employment", label="Employment History",
        completed=employment_done, required=True,
    ))

    # Immigration History
    # TODO: replace with actual immigration history model check
    immigration_done = False
    sections.append(ReadinessSection(
        key="immigration", label="Immigration History",
        completed=immigration_done, required=True,
    ))

    # Dependents (optional)
    sections.append(ReadinessSection(
        key="dependents", label="Dependents",
        completed=False, required=False,
    ))

    required = [s for s in sections if s.required]
    done     = [s for s in required if s.completed]
    pct      = round((len(done) / len(required)) * 100) if required else 0

    return pct, sections


# ─────────────────────────────────────────────────────────────────────────────
# BUILD CASE PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

async def _build_case_summary(
    db: AsyncSession,
    app: "Application",
    visa_type: "VisaType | None",
) -> CaseSummary:
    """
    Build the visual stage pipeline from the application's current_stage
    and its status history.
    """
    current_key = app.current_stage or "profile_eligibility"
    current_idx = STAGE_KEY_TO_IDX.get(current_key, 0)

    # Fetch status history for timestamps
    history_result = await db.execute(
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == app.id)
        .order_by(ApplicationStatusHistory.created_at.asc())
    )
    history_rows = history_result.scalars().all()

    # Build a map: stage_key → (started_at, completed_at, note)
    stage_timestamps: dict[str, dict] = {}
    for h in history_rows:
        stage = h.stage or ""
        if stage not in stage_timestamps:
            stage_timestamps[stage] = {"started_at": _iso(h.created_at), "note": h.note}
        # The last entry for a stage is when it was "completed" (next stage started)
        stage_timestamps[stage]["latest"] = _iso(h.created_at)

    stages: list[CaseStage] = []
    for i, (key, label, _pct) in enumerate(PIPELINE_STAGES):
        ts = stage_timestamps.get(key, {})
        if i < current_idx:
            status = "completed"
        elif i == current_idx:
            status = "active"
        else:
            status = "upcoming"

        stages.append(CaseStage(
            key=key,
            label=label,
            status=status,
            started_at=ts.get("started_at"),
            completed_at=ts.get("latest") if status == "completed" else None,
            note=ts.get("note") if status == "active" else None,
        ))

    # Overall progress — based on current stage position
    overall_progress = PIPELINE_STAGES[current_idx][2] if current_idx < len(PIPELINE_STAGES) else 100

    visa_code  = visa_type.code if visa_type else "H-1B"
    visa_label = visa_type.name if visa_type and visa_type.name else f"{visa_code} Application"

    return CaseSummary(
        application_id=str(app.id),
        visa_type=visa_code,
        visa_label=visa_label,
        case_number=getattr(app, "receipt_number", None),
        filed_date=_iso(app.created_at) if app.created_at else None,
        current_stage=current_key,
        stages=stages,
        overall_progress=overall_progress,
    )


# ─────────────────────────────────────────────────────────────────────────────
# BUILD ACTION ITEMS — derived from documents + application state
# ─────────────────────────────────────────────────────────────────────────────

def _build_action_items(
    documents: list,
    app: "Application | None",
) -> list[ActionItem]:
    """
    Generate actionable tasks the employee should complete.
    Sources: documents needing action, application stage requirements.
    """
    items: list[ActionItem] = []
    counter = 0

    # 1. Documents that need re-upload (rejected)
    for doc in documents:
        if doc.status == "rejected":
            counter += 1
            items.append(ActionItem(
                id=f"act_doc_rej_{counter}",
                title=f"Re-upload {_doc_display_name(doc)}",
                description=doc.rejection_reason if hasattr(doc, "rejection_reason") and doc.rejection_reason else "This document was rejected — please upload a corrected version.",
                category="document",
                priority="urgent",
                due_date=None,
                days_left=None,
                route="/documents/upload",
                completed=False,
            ))

    # 2. Documents still pending_review — no action needed, but inform
    #    (we don't add these as action items — they're waiting on attorney)

    # 3. Application-level action items based on current stage
    if app and not app.is_draft:
        stage = app.current_stage or ""

        # If in document_collection and docs are missing, prompt upload
        if stage == "document_collection":
            counter += 1
            items.append(ActionItem(
                id=f"act_stage_{counter}",
                title="Complete document uploads",
                description="Your case is in the Document Collection stage. Upload all required documents to proceed.",
                category="document",
                priority="high",
                due_date=None,
                days_left=None,
                route="/documents/upload",
                completed=False,
            ))

        # If in petition_prep, prompt form review
        if stage == "petition_prep":
            counter += 1
            items.append(ActionItem(
                id=f"act_stage_{counter}",
                title="Review petition draft",
                description="Your attorney has prepared the petition. Review the draft for accuracy.",
                category="form",
                priority="high",
                due_date=None,
                days_left=None,
                route=f"/applications/{app.id}",
                completed=False,
            ))

        # If action_needed status
        if app.status == "action_needed":
            counter += 1
            items.append(ActionItem(
                id=f"act_rfe_{counter}",
                title="Respond to action request",
                description="Your case requires additional information. Check your messages for details.",
                category="review",
                priority="urgent",
                due_date=None,
                days_left=None,
                route="/messages",
                completed=False,
            ))

    return items


# ─────────────────────────────────────────────────────────────────────────────
# BUILD DEADLINES — derived from application stage + estimated timelines
# ─────────────────────────────────────────────────────────────────────────────

def _build_deadlines(
    app: "Application | None",
    action_items: list[ActionItem],
) -> list[Deadline]:
    """
    Generate upcoming deadlines from application state.
    In production, these would come from a Deadlines/Tasks model.
    For now we derive them from the application's stage and created_at.
    """
    deadlines: list[Deadline] = []

    if not app or app.is_draft:
        return deadlines

    now = _now()
    filed = app.created_at or now
    if filed.tzinfo is None:
        filed = filed.replace(tzinfo=timezone.utc)

    # Generate stage-based estimated deadlines
    stage = app.current_stage or "profile_eligibility"
    current_idx = STAGE_KEY_TO_IDX.get(stage, 0)

    # Estimated days from filing to each stage completion
    STAGE_EST_DAYS: dict[str, int] = {
        "profile_eligibility": 7,
        "document_collection": 21,
        "lca_filing":          35,
        "petition_prep":       50,
        "uscis_filing":        60,
        "uscis_review":        120,
        "decision":            180,
    }

    counter = 0
    for i, (key, label, _pct) in enumerate(PIPELINE_STAGES):
        if i <= current_idx:
            continue  # already passed this stage

        est_days = STAGE_EST_DAYS.get(key, 30)
        est_date = filed + timedelta(days=est_days)
        days_left = _days_between(est_date)

        if days_left > 90:
            continue  # too far out

        counter += 1
        deadlines.append(Deadline(
            id=f"dl_{counter}",
            title=f"{label} (estimated)",
            date=_iso(est_date),
            days_left=days_left,
            urgency=_deadline_urgency(days_left),
            owner="attorney" if key in ("lca_filing", "petition_prep", "uscis_filing") else "employee",
            description=f"Estimated target for {label.lower()} stage.",
        ))

    # Sort by days_left ascending
    deadlines.sort(key=lambda d: d.days_left)
    return deadlines


# ─────────────────────────────────────────────────────────────────────────────
# BUILD CASE TEAM — from application's assigned users
# ─────────────────────────────────────────────────────────────────────────────

async def _build_case_team(
    db: AsyncSession,
    app: "Application | None",
) -> list[CaseTeamMember]:
    """
    Look up the assigned attorney and HR contact from the application.
    Falls back gracefully if fields don't exist on the model.
    """
    team: list[CaseTeamMember] = []

    if not app:
        return team

    # Attorney — check if application has assigned_attorney_id
    attorney_id = getattr(app, "assigned_attorney_id", None)
    if attorney_id:
        result = await db.execute(select(User).where(User.id == attorney_id))
        attorney = result.scalars().first()
        if attorney:
            team.append(CaseTeamMember(
                id=str(attorney.id),
                name=f"{attorney.first_name or ''} {attorney.last_name or ''}".strip() or attorney.email,
                role="Immigration Attorney",
                email=attorney.email,
                phone=getattr(attorney, "phone", None),
                available=True,
            ))

    # HR Contact — from assigned_hr_id
    hr_id = getattr(app, "assigned_hr_id", None)
    if hr_id:
        result = await db.execute(select(User).where(User.id == hr_id))
        hr_user = result.scalars().first()
        if hr_user:
            team.append(CaseTeamMember(
                id=str(hr_user.id),
                name=f"{hr_user.first_name or ''} {hr_user.last_name or ''}".strip() or hr_user.email,
                role="HR Contact",
                email=hr_user.email,
                phone=getattr(hr_user, "phone", None),
                available=True,
            ))

    return team


# ─────────────────────────────────────────────────────────────────────────────
# BUILD ACTIVITY FEED
# ─────────────────────────────────────────────────────────────────────────────

async def _build_activity(
    db: AsyncSession,
    user_id: uuid.UUID,
    app: "Application | None",
) -> list[ActivityItemV2]:
    """
    Merge DocumentActivity + ApplicationStatusHistory into a single
    reverse-chronological feed.
    """
    items: list[ActivityItemV2] = []

    # Document activity
    doc_activity_result = await db.execute(
        select(DocumentActivity)
        .join(Document, DocumentActivity.document_id == Document.id)
        .where(Document.user_id == user_id)
        .order_by(DocumentActivity.created_at.desc())
        .limit(15)
    )
    for a in doc_activity_result.scalars().all():
        actor = "You"
        if hasattr(a, "performed_by_id") and a.performed_by_id and a.performed_by_id != user_id:
            actor = "Case Team"  # could look up name if needed

        items.append(ActivityItemV2(
            id=str(a.id),
            type=ACTIVITY_TYPE_MAP.get(a.action, "case_note"),
            title=a.action.replace("_", " ").title() if a.action else "Activity",
            description=a.note or "Document activity",
            timestamp=_iso(a.created_at),
            actor=actor,
        ))

    # Application status history
    if app:
        history_result = await db.execute(
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id == app.id)
            .order_by(ApplicationStatusHistory.created_at.desc())
            .limit(10)
        )
        for h in history_result.scalars().all():
            items.append(ActivityItemV2(
                id=str(h.id),
                type="stage_advanced",
                title=f"Status: {(h.status or '').replace('_', ' ').title()}",
                description=h.note or f"Stage: {h.stage or 'unknown'}",
                timestamp=_iso(h.created_at),
                actor="System",
            ))

    # Sort all by timestamp descending, limit to 15
    items.sort(key=lambda x: x.timestamp, reverse=True)
    return items[:15]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SERVICE
# ─────────────────────────────────────────────────────────────────────────────

async def service_get_dashboard(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> DashboardResponse:
    """
    Assembles the full employee dashboard.

    Queries:
      1. Applications  — active count, latest for pipeline + sponsor
      2. Documents     — full list + counts
      3. UserProfile   — readiness sections
      4. VisaType      — processing time estimate
      5. Activity      — merged doc + status history feed
      6. Case team     — from assigned attorney/HR
    Derives:
      - Action items   — from document statuses + app stage
      - Deadlines      — from app stage + estimated timelines
      - Payments       — placeholder until Payment model is built
    """
    now = _now()

    # ── 1. Applications ───────────────────────────────────────────────────────
    active_statuses = ["in_progress", "action_needed", "rfe_response", "submitted"]

    active_count_result = await db.execute(
        select(func.count(Application.id))
        .where(Application.user_id == user_id)
        .where(Application.status.in_(active_statuses))
    )
    active_applications = active_count_result.scalar() or 0

    # Latest non-draft application
    latest_app_result = await db.execute(
        select(Application)
        .where(Application.user_id == user_id)
        .where(Application.is_draft == False)  # noqa: E712
        .order_by(Application.created_at.desc())
        .limit(1)
    )
    latest_app = latest_app_result.scalars().first()

    # ── 2. Visa type info ─────────────────────────────────────────────────────
    visa_target_result = await db.execute(
        select(UserVisaTarget)
        .where(UserVisaTarget.user_id == user_id)
        .where(UserVisaTarget.is_primary == True)  # noqa: E712
        .limit(1)
    )
    primary_target = visa_target_result.scalars().first()

    if not primary_target:
        any_target = await db.execute(
            select(UserVisaTarget).where(UserVisaTarget.user_id == user_id).limit(1)
        )
        primary_target = any_target.scalars().first()

    visa_type = None
    if primary_target:
        vt_result = await db.execute(
            select(VisaType).where(VisaType.code == primary_target.visa_type_code)
        )
        visa_type = vt_result.scalars().first()

    processing_days_estimated = (
        visa_type.typical_processing_days
        if visa_type and visa_type.typical_processing_days
        else 90
    )
    processing_type = "Standard Processing"

    # Days elapsed since filing
    processing_days_elapsed = 0
    if latest_app and latest_app.created_at:
        filed = latest_app.created_at
        if filed.tzinfo is None:
            filed = filed.replace(tzinfo=timezone.utc)
        processing_days_elapsed = max(0, (now - filed).days)

    # ── 3. Documents — full list ──────────────────────────────────────────────
    docs_result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    all_docs = docs_result.scalars().unique().all()

    documents_total    = len(all_docs)
    documents_verified = sum(1 for d in all_docs if d.status == "verified")
    documents_action   = sum(1 for d in all_docs if d.status in ("rejected", "pending_review"))

    document_items = [
        DocumentSummaryItem(
            id=str(d.id),
            name=_doc_display_name(d),
            category=_doc_category(d),
            status=_doc_status(d),
            uploaded_at=_iso(d.created_at) if d.created_at else None,
            note=getattr(d, "rejection_reason", None) or getattr(d, "notes", None),
        )
        for d in all_docs
    ]

    # ── 4. Profile readiness ──────────────────────────────────────────────────
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalars().first()
    readiness_pct, readiness_sections = _build_readiness(profile)

    # ── 5. Case summary (pipeline) ────────────────────────────────────────────
    case_summary = None
    if latest_app:
        case_summary = await _build_case_summary(db, latest_app, visa_type)

    # ── 6. Action items ───────────────────────────────────────────────────────
    action_items = _build_action_items(all_docs, latest_app)

    # ── 7. Deadlines ──────────────────────────────────────────────────────────
    deadlines = _build_deadlines(latest_app, action_items)

    # ── 8. Next deadline for KPI card ─────────────────────────────────────────
    if deadlines:
        next_dl = deadlines[0]
        next_deadline_label = next_dl.title
        next_deadline_date  = next_dl.date
        next_deadline_days  = next_dl.days_left
    else:
        next_deadline_label = "No upcoming deadlines"
        next_deadline_date  = _iso(now + timedelta(days=365))
        next_deadline_days  = 999

    # ── 9. Sponsor info ───────────────────────────────────────────────────────
    sponsor_name = "No Sponsor Yet"
    sponsor_verified = False
    if latest_app:
        sponsor_name = getattr(latest_app, "sponsor_employer", None) or "No Sponsor Yet"
        sponsor_verified = bool(getattr(latest_app, "assigned_hr_id", None))

    # ── 10. Compliance score — ratio of verified docs + profile readiness ─────
    doc_score = round((documents_verified / documents_total) * 50) if documents_total > 0 else 0
    compliance_score = min(100, doc_score + round(readiness_pct * 0.5))

    # ── 11. Activity ──────────────────────────────────────────────────────────
    activity = await _build_activity(db, user_id, latest_app)

    # ── 12. Case team ─────────────────────────────────────────────────────────
    case_team = await _build_case_team(db, latest_app)

    # ── 13. Payments — placeholder until Payment model exists ─────────────────
    # TODO: Replace with real queries once app/models/payment.py is built.
    payments = PaymentSummary(
        total_fees=0,
        paid=0,
        pending=0,
        next_payment_label=None,
        next_payment_amount=None,
        next_payment_due=None,
    )

    # ── Assemble response ─────────────────────────────────────────────────────
    stats = DashboardStats(
        active_applications=active_applications,
        documents_verified=documents_verified,
        documents_total=documents_total,
        documents_action_required=documents_action,
        processing_days_elapsed=processing_days_elapsed,
        processing_days_estimated=processing_days_estimated,
        processing_type=processing_type,
        next_deadline_label=next_deadline_label,
        next_deadline_date=next_deadline_date,
        next_deadline_days=next_deadline_days,
        profile_readiness=readiness_pct,
        sponsor_name=sponsor_name,
        sponsor_verified=sponsor_verified,
        compliance_score=compliance_score,
    )

    return DashboardResponse(
        stats=stats,
        case_summary=case_summary,
        action_items=action_items,
        documents=document_items,
        deadlines=deadlines,
        payments=payments,
        case_team=case_team,
        activity=activity,
        readiness=readiness_sections,
    )