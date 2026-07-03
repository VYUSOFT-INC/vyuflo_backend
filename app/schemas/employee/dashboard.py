# app/schemas/dashboard.py
#
# Employee dashboard response models.
# Replaces the original 3-model schema with the full payload
# needed by the production Dashboard.tsx.

from typing import Optional
from pydantic import BaseModel


# ── Case Pipeline ─────────────────────────────────────────────────────────────

class CaseStage(BaseModel):
    key: str                             # "profile_eligibility", "lca_filing", etc.
    label: str                           # human-readable
    status: str                          # "completed" | "active" | "upcoming" | "blocked"
    started_at: Optional[str] = None     # ISO datetime
    completed_at: Optional[str] = None
    note: Optional[str] = None           # e.g. "LCA posted — 7 days remaining"


class CaseSummary(BaseModel):
    application_id: str
    visa_type: str                       # "H-1B"
    visa_label: str                      # "H-1B Specialty Occupation"
    case_number: Optional[str] = None    # USCIS receipt number
    filed_date: Optional[str] = None
    current_stage: str
    stages: list[CaseStage]
    overall_progress: int                # 0–100


# ── KPI Stats ─────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    active_applications: int
    documents_verified: int
    documents_total: int
    documents_action_required: int

    processing_days_elapsed: int         # days since application filed
    processing_days_estimated: int       # from visa_types.typical_processing_days
    processing_type: str                 # "Standard Processing" | "Premium Processing"

    next_deadline_label: str
    next_deadline_date: str              # ISO datetime
    next_deadline_days: int

    profile_readiness: int               # 0–100
    sponsor_name: str
    sponsor_verified: bool
    compliance_score: int                # 0–100


# ── Action Items ──────────────────────────────────────────────────────────────

class ActionItem(BaseModel):
    id: str
    title: str
    description: str
    category: str      # "document" | "form" | "payment" | "appointment" | "review" | "info"
    priority: str      # "urgent" | "high" | "medium" | "low"
    due_date: Optional[str] = None
    days_left: Optional[int] = None
    route: Optional[str] = None
    completed: bool


# ── Documents Overview ────────────────────────────────────────────────────────

class DocumentSummaryItem(BaseModel):
    id: str
    name: str
    category: str      # "Identity", "Education", "Employment", "Petition"
    status: str        # "verified" | "pending_review" | "action_required" | "not_uploaded" | "rejected"
    uploaded_at: Optional[str] = None
    note: Optional[str] = None


# ── Deadlines ─────────────────────────────────────────────────────────────────

class Deadline(BaseModel):
    id: str
    title: str
    date: str          # ISO datetime
    days_left: int     # negative if overdue
    urgency: str       # "overdue" | "critical" | "soon" | "normal"
    owner: str         # "employee" | "attorney" | "employer" | "uscis"
    description: Optional[str] = None


# ── Payment Summary ───────────────────────────────────────────────────────────

class PaymentSummary(BaseModel):
    total_fees: int
    paid: int
    pending: int
    next_payment_label: Optional[str] = None
    next_payment_amount: Optional[int] = None
    next_payment_due: Optional[str] = None


# ── Case Team ─────────────────────────────────────────────────────────────────

class CaseTeamMember(BaseModel):
    id: str
    name: str
    role: str          # "Immigration Attorney", "Paralegal", "HR Contact"
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    available: bool


# ── Activity ──────────────────────────────────────────────────────────────────

class ActivityItemV2(BaseModel):
    id: str
    type: str          # "stage_advanced" | "document_uploaded" | "document_verified" | etc.
    title: str
    description: str
    timestamp: str     # ISO datetime
    actor: Optional[str] = None  # "Attorney Smith", "System", "You"


# ── Profile Readiness ─────────────────────────────────────────────────────────

class ReadinessSection(BaseModel):
    key: str
    label: str
    completed: bool
    required: bool


# ── Aggregate Dashboard Response ──────────────────────────────────────────────

class DashboardResponse(BaseModel):
    stats: DashboardStats
    case_summary: Optional[CaseSummary] = None
    action_items: list[ActionItem]
    documents: list[DocumentSummaryItem]
    deadlines: list[Deadline]
    payments: PaymentSummary
    case_team: list[CaseTeamMember]
    activity: list[ActivityItemV2]
    readiness: list[ReadinessSection]


# ── Legacy models (keep for backward compat until old frontend is removed) ───

class LegacyActivityItem(BaseModel):
    """Old activity shape — used by the original Dashboard.tsx."""
    id: str
    title: str
    description: str
    timestamp: str
    color: str


class GuidanceItem(BaseModel):
    """Static guidance library item."""
    id: str
    tag: str
    tag_color: str
    icon_type: str
    title: str
    description: str