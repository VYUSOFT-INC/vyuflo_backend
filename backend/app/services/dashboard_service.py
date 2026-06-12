import uuid
from datetime import datetime, timezone
 
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.models.visamodels import (
    Application,
    ApplicationStatusHistory,
    Document,
    DocumentActivity,
    UserProfile,
    UserVisaTarget,
    VisaType,
)
from app.schemas.dashboard import ActivityItem, DashboardResponse, DashboardStats, GuidanceItem
 
# ── Stage label map ───────────────────────────────────────────────────────────
STAGE_LABELS = {
    "profile_eligibility": "Profile Review",
    "documentation":       "Documentation",
    "lca_filing":          "LCA Filed",
    "uscis_submission":    "USCIS Review",
    None:                  "In Progress",
}
 
# ── Guidance library — static content keyed by visa code ─────────────────────
GUIDANCE_BY_VISA: dict[str, list[dict]] = {
    "H-1B": [
        {"id":"g1","tag":"Required","tag_color":"blue",  "icon_type":"doc", "title":"LCA Overview",       "description":"Understanding the Labor Condition Application process and timelines."},
        {"id":"g2","tag":"Optional","tag_color":"purple","icon_type":"cap", "title":"Degree Evaluation",  "description":"When and how to get your foreign degree evaluated for US equivalent."},
        {"id":"g3","tag":"Tip",     "tag_color":"gray",  "icon_type":"user","title":"Photo Requirements", "description":"USCIS passport-style photo specifications and common mistakes."},
        {"id":"g4","tag":"Info",    "tag_color":"gray",  "icon_type":"info","title":"Filing Fees 2024",   "description":"Updated fee schedule for I-129 and premium processing."},
    ],
    "F-1-OPT": [
        {"id":"g1","tag":"Required","tag_color":"blue",  "icon_type":"doc", "title":"OPT Application",    "description":"Step-by-step guide to applying for Optional Practical Training."},
        {"id":"g2","tag":"Required","tag_color":"blue",  "icon_type":"doc", "title":"I-20 Update",        "description":"How to get your OPT I-20 from your DSO before applying."},
        {"id":"g3","tag":"Tip",     "tag_color":"gray",  "icon_type":"user","title":"Timeline",           "description":"Apply 90 days before your program end date — no later."},
        {"id":"g4","tag":"Info",    "tag_color":"gray",  "icon_type":"info","title":"EAD Card",           "description":"Your Employment Authorization Document — what it means and how to use it."},
    ],
    "O-1A": [
        {"id":"g1","tag":"Required","tag_color":"blue",  "icon_type":"doc", "title":"Evidence Package",   "description":"The 8 criteria — what counts as extraordinary ability evidence."},
        {"id":"g2","tag":"Required","tag_color":"blue",  "icon_type":"doc", "title":"Support Letters",    "description":"How to secure letters from experts in your field."},
        {"id":"g3","tag":"Tip",     "tag_color":"gray",  "icon_type":"user","title":"Advisory Opinion",   "description":"When and why to get a peer group advisory opinion letter."},
        {"id":"g4","tag":"Info",    "tag_color":"gray",  "icon_type":"info","title":"Processing Time",    "description":"Standard vs premium processing — timelines and fees for O-1A."},
    ],
}
 
_DEFAULT_GUIDANCE = [
    {"id":"g1","tag":"Required","tag_color":"blue",  "icon_type":"doc", "title":"Document Checklist",    "description":"Essential documents required for your visa application."},
    {"id":"g2","tag":"Tip",     "tag_color":"gray",  "icon_type":"user","title":"Photo Requirements",    "description":"USCIS passport-style photo specifications and common mistakes."},
    {"id":"g3","tag":"Info",    "tag_color":"gray",  "icon_type":"info","title":"Filing Fees",           "description":"Current USCIS fee schedule for your visa category."},
    {"id":"g4","tag":"Optional","tag_color":"purple","icon_type":"cap", "title":"Premium Processing",    "description":"When and how to request premium processing to speed up your case."},
]
 
# ── Activity color map ────────────────────────────────────────────────────────
def _activity_color(action: str) -> str:
    return {
        "uploaded":        "#5269f2",
        "verified":        "#10b981",
        "status_changed":  "#5269f2",
        "rejected":        "#ef4444",
        "version_updated": "#f59e0b",
        "ocr_completed":   "#5269f2",
        "downloaded":      "#cbd5e1",
        "viewed":          "#cbd5e1",
    }.get(action, "#cbd5e1")
 
 
def _action_title(action: str) -> str:
    return {
        "uploaded":        "Document Uploaded",
        "verified":        "Document Verified",
        "status_changed":  "Status Updated",
        "rejected":        "Document Rejected",
        "version_updated": "Document Updated",
        "ocr_completed":   "OCR Completed",
        "downloaded":      "Document Downloaded",
        "viewed":          "Document Viewed",
    }.get(action, action.replace("_", " ").title())
 
 
def _profile_readiness(profile) -> int:
    """
    Calculate profile readiness % from UserProfile fields.
    Matches the 3 items shown in the Figma donut:
      - Personal Info (full_legal_name + nationality)    → 33%
      - Passport (date_of_birth)                         → 33%
      - Education History (not in profile yet)           → 0% (always incomplete)
    """
    score = 0
    if profile and profile.full_legal_name and profile.nationality:
        score += 34
    if profile and profile.date_of_birth:
        score += 33
    # Education history — not yet in model, always 0
    return score
 
 
# ── Main service function ─────────────────────────────────────────────────────
 
async def service_get_dashboard(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """
    Assembles the full dashboard response for the given user.
    Queries:
      1. Applications — count active, find latest for sponsor info
      2. Documents    — count verified vs total, count action required
      3. DocumentActivity — last 10 activity events for timeline
      4. UserProfile  — profile readiness %
      5. UserVisaTarget + VisaType — processing days + guidance library
    """
 
    # ── 1. Applications ───────────────────────────────────────────────────────
    # Active = not draft, not rejected, not withdrawn
    active_statuses = ["in_progress", "action_needed", "rfe_response", "submitted"]
 
    active_apps_result = await db.execute(
        select(func.count(Application.id))
        .where(Application.user_id == user_id)
        .where(Application.status.in_(active_statuses))
    )
    active_applications = active_apps_result.scalar() or 0
 
    # Latest non-draft application — for sponsor info + processing time
    latest_app_result = await db.execute(
        select(Application)
        .where(Application.user_id == user_id)
        .where(Application.is_draft == False)             # noqa: E712
        .order_by(Application.created_at.desc())
        .limit(1)
    )
    latest_app = latest_app_result.scalars().first()
 
    # ── 2. Documents ──────────────────────────────────────────────────────────
    docs_total_result = await db.execute(
        select(func.count(Document.id))
        .where(Document.user_id == user_id)
    )
    documents_total = docs_total_result.scalar() or 0
 
    docs_verified_result = await db.execute(
        select(func.count(Document.id))
        .where(Document.user_id == user_id)
        .where(Document.status == "verified")
    )
    documents_verified = docs_verified_result.scalar() or 0
 
    # Action required = rejected OR pending_review
    docs_action_result = await db.execute(
        select(func.count(Document.id))
        .where(Document.user_id == user_id)
        .where(Document.status.in_(["rejected", "pending_review"]))
    )
    documents_action_required = docs_action_result.scalar() or 0
 
    # ── 3. Visa type → processing days + guidance ─────────────────────────────
    # Get user's primary visa target
    visa_target_result = await db.execute(
        select(UserVisaTarget)
        .where(UserVisaTarget.user_id == user_id)
        .where(UserVisaTarget.is_primary == True)         # noqa: E712
        .limit(1)
    )
    primary_target = visa_target_result.scalars().first()
 
    # Fallback — get any visa target if no primary
    if not primary_target:
        any_target_result = await db.execute(
            select(UserVisaTarget)
            .where(UserVisaTarget.user_id == user_id)
            .limit(1)
        )
        primary_target = any_target_result.scalars().first()
 
    # Get VisaType details
    visa_type = None
    if primary_target:
        vt_result = await db.execute(
            select(VisaType)
            .where(VisaType.code == primary_target.visa_type_code)
        )
        visa_type = vt_result.scalars().first()
 
    processing_days = visa_type.typical_processing_days if visa_type and visa_type.typical_processing_days else 45
    processing_type = "Standard Processing"
 
    # Guidance library — keyed by visa code, fallback to default
    visa_code     = visa_type.code if visa_type else "H-1B"
    guidance_raw  = GUIDANCE_BY_VISA.get(visa_code, _DEFAULT_GUIDANCE)
    guidance_items = [GuidanceItem(**g) for g in guidance_raw]
 
    # ── 4. Sponsor info ───────────────────────────────────────────────────────
    sponsor_name     = latest_app.sponsor_employer if latest_app and latest_app.sponsor_employer else "No Sponsor Yet"
    sponsor_stage    = STAGE_LABELS.get(latest_app.current_stage if latest_app else None, "In Progress")
    sponsor_verified = bool(latest_app and latest_app.assigned_hr_id) if latest_app else False
 
    # ── 5. Profile readiness ──────────────────────────────────────────────────
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalars().first()
    profile_readiness_pct = _profile_readiness(profile)
 
    # ── 6. Recent Activity — DocumentActivity (last 10) ───────────────────────
    activity_result = await db.execute(
        select(DocumentActivity)
        .join(Document, DocumentActivity.document_id == Document.id)
        .where(Document.user_id == user_id)
        .order_by(DocumentActivity.created_at.desc())
        .limit(10)
    )
    activity_rows = activity_result.scalars().all()
 
    # If no doc activity yet, try ApplicationStatusHistory
    if not activity_rows and latest_app:
        history_result = await db.execute(
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id == latest_app.id)
            .order_by(ApplicationStatusHistory.created_at.desc())
            .limit(10)
        )
        history_rows = history_result.scalars().all()
 
        activity_items = [
            ActivityItem(
                id        = str(h.id),
                title     = f"Status: {h.status.replace('_', ' ').title()}",
                description = h.note or f"Stage: {STAGE_LABELS.get(h.stage, h.stage)}",
                timestamp = h.created_at.isoformat() if h.created_at else datetime.now(timezone.utc).isoformat(),
                color     = "#5269f2",
            )
            for h in history_rows
        ]
    else:
        activity_items = [
            ActivityItem(
                id          = str(a.id),
                title       = _action_title(a.action),
                description = a.note or "Document activity",
                timestamp   = a.created_at.isoformat() if a.created_at else datetime.now(timezone.utc).isoformat(),
                color       = _activity_color(a.action),
            )
            for a in activity_rows
        ]
 
    # ── Build response ────────────────────────────────────────────────────────
    stats = DashboardStats(
        active_applications       = active_applications,
        documents_verified        = documents_verified,
        documents_total           = documents_total,
        documents_action_required = documents_action_required,
        processing_days           = processing_days,
        processing_type           = processing_type,
        sponsor_name              = sponsor_name,
        sponsor_stage             = sponsor_stage,
        sponsor_verified          = sponsor_verified,
        profile_readiness         = profile_readiness_pct,
    )
 
    return DashboardResponse(
        stats    = stats,
        activity = activity_items,
        guidance = guidance_items,
    )