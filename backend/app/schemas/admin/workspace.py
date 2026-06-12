"""
workspace_schema.py — Pydantic v2 schemas for ADMIN-10 Workspace Dashboard.

FILE LOCATION
    app/schemas/workspace_schema.py

CORRECTED FOR visamodels.py (57 tables)
    ✅ Deadline  : urgency field (critical/high/medium/low), no status column
                   overdue is computed → due_date < now AND is_completed=False
    ✅ Document  : file_size_bytes (was file_size_kb), file_type (was file_format)
                   pending statuses → "pending_review" | "under_review"
    ✅ AuditLog  : event_type column REMOVED — field dropped from new models
    ✅ New tables: application_comments, employer_profiles, attorney_profiles
                   acknowledged but not required for existing dashboard widgets

SECTIONS
    1.  Shared mini-objects         (reused across multiple sections)
    2.  KPI Summary Cards           → GET /workspace/kpi
    3.  Recent Applications         → GET /workspace/recent-applications
    4.  My Tasks                    → GET /workspace/my-tasks
    5.  Upcoming Deadlines          → GET /workspace/upcoming-deadlines
    6.  Activity Feed               → GET /workspace/activity-feed
    7.  Case Pipeline Chart         → GET /workspace/case-pipeline
    8.  Pending Documents           → GET /workspace/pending-documents
    9.  Team Workload               → GET /workspace/team
    10. Full Dashboard Aggregation  → GET /workspace/dashboard
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# 1. SHARED MINI-OBJECTS
# =============================================================================

class UserMiniResponse(BaseModel):
    """
    Compact user object embedded in applications, tasks, deadlines, etc.
    profile_picture_url  →  user_profiles.profile_picture_url  (LEFT JOIN)
    """
    model_config = ConfigDict(from_attributes=True)

    id:                  uuid.UUID
    first_name:          str
    last_name:           str
    email:               str
    profile_picture_url: Optional[str] = None


# =============================================================================
# 2. KPI SUMMARY CARDS
#    Powers the four stat cards at the top of ADMIN-10.
#
#    Card 1 — Total Applications
#    Card 2 — Active Cases        (status IN in_progress / action_needed / rfe_response)
#    Card 3 — Pending Tasks       (ApplicationTask.is_completed = False, scoped)
#    Card 4 — Overdue Deadlines   (Deadline.due_date < now AND is_completed=False
#                                  AND is_dismissed=False, scoped)
# =============================================================================

class WorkspaceKPIResponse(BaseModel):
    """Response for GET /workspace/kpi"""

    total_applications:          int
    active_cases:                int
    pending_tasks:               int
    overdue_deadlines:           int

    # Week-over-week delta badges — "+12% this week" (null = not enough history)
    applications_delta_pct:      Optional[float] = None
    active_cases_delta_pct:      Optional[float] = None
    pending_tasks_delta_pct:     Optional[float] = None
    overdue_deadlines_delta_pct: Optional[float] = None


# =============================================================================
# 3. RECENT APPLICATIONS TABLE
#    Powers the main applications table on ADMIN-10.
#
#    UI columns:
#      App #  |  Applicant  |  Visa Type  |  Status  |  Progress  |
#      Assignees  |  Due Date  |  Action Required badge
# =============================================================================

class RecentApplicationItem(BaseModel):
    """One row in the Recent Applications table."""

    id:                   uuid.UUID
    application_number:   str                       # "VF-2024-8921"
    visa_type_name:       str                       # "H-1B Specialty Occupation"
    visa_type_code:       str                       # "H-1B"
    status:               str                       # application_status_enum
    current_stage:        Optional[str]  = None     # application_stage_enum
    progress_percent:     int                       # 0–100
    due_date:             Optional[date] = None
    has_action_required:  bool           = False
    action_required_note: Optional[str]  = None

    applicant:            UserMiniResponse
    assigned_attorney:    Optional[UserMiniResponse] = None
    assigned_hr:          Optional[UserMiniResponse] = None

    created_at:           datetime
    updated_at:           datetime


class RecentApplicationsResponse(BaseModel):
    """Response for GET /workspace/recent-applications"""

    items:       List[RecentApplicationItem]
    total:       int
    page:        int
    limit:       int
    total_pages: int


# =============================================================================
# 4. MY TASKS CHECKLIST
#    Powers the "My Tasks" widget on ADMIN-10.
#    Source: application_tasks scoped through assigned applications.
# =============================================================================

class WorkspaceTaskItem(BaseModel):
    """One row in the My Tasks checklist."""

    id:                  uuid.UUID
    task_name:           str
    description:         Optional[str]      = None
    is_completed:        bool
    is_required:         bool
    completed_at:        Optional[datetime] = None

    # Parent application context
    application_id:      uuid.UUID
    application_number:  str                        # "VF-2024-8921"
    applicant_name:      str                        # "John Doe"

    # Linked document (when task satisfied by an upload)
    document_id:         Optional[uuid.UUID] = None
    document_file_name:  Optional[str]       = None

    created_at:          datetime
    updated_at:          datetime


class MyTasksResponse(BaseModel):
    """Response for GET /workspace/my-tasks"""

    items:           List[WorkspaceTaskItem]
    total:           int
    completed_count: int
    pending_count:   int
    page:            int
    limit:           int
    total_pages:     int


# =============================================================================
# 5. UPCOMING DEADLINES SIDEBAR
#    Powers the deadline list on ADMIN-10.
#
#    visamodels.py CHANGES vs old models:
#      • urgency  replaces  priority  (new enum: critical/high/medium/low)
#      • No status column — overdue = due_date < now AND is_completed=False
#      • is_dismissed replaces dismissed status value
#
#    UI colour mapping:
#      urgency = "critical" → red   badge + red due-date text
#      urgency = "high"     → amber badge
#      urgency = "medium"   → blue  badge
#      urgency = "low"      → grey  badge
#      days_until_due < 0   → overdue, shown as negative number
# =============================================================================

class UpcomingDeadlineItem(BaseModel):
    """One deadline card in the sidebar."""

    id:                  uuid.UUID
    title:               str
    deadline_type:       str                        # deadline_type_enum value
    urgency:             str                        # "critical"|"high"|"medium"|"low"
    is_completed:        bool
    is_dismissed:        bool
    due_date:            datetime
    days_until_due:      int                        # negative = overdue
    is_overdue:          bool                       # computed: due_date < now AND not completed

    # Optional application link
    application_id:      Optional[uuid.UUID] = None
    application_number:  Optional[str]       = None

    # Deadline owner
    user_id:             uuid.UUID
    user_name:           str

    created_at:          datetime


class UpcomingDeadlinesResponse(BaseModel):
    """Response for GET /workspace/upcoming-deadlines"""

    items:          List[UpcomingDeadlineItem]
    total:          int
    overdue_count:  int     # due_date < now AND is_completed=False AND is_dismissed=False
    critical_count: int     # urgency="critical" AND is_completed=False
    page:           int
    limit:          int
    total_pages:    int


# =============================================================================
# 6. ACTIVITY FEED
#    Powers the "Recent Activity" stream on ADMIN-10.
#    Source: audit_logs table (immutable, append-only).
#
#    visamodels.py CHANGE vs old models:
#      • event_type column REMOVED from audit_logs — filter param dropped
#      • severity and resource_type filters still available
# =============================================================================

class ActivityFeedItem(BaseModel):
    """One event in the activity stream."""

    id:            uuid.UUID
    action:        str                        # "application.status_changed"
    description:   Optional[str]  = None     # "VF-2024-8921 approved"
    resource_type: Optional[str]  = None     # "application"|"document"|"user"|…
    resource_id:   Optional[uuid.UUID] = None
    severity:      str                        # "info"|"warning"|"critical"

    # Actor (joined from users + denormalized snapshot on audit_logs)
    actor_id:      Optional[uuid.UUID] = None
    actor_name:    Optional[str]       = None   # "Alexandra Smith" / "System"
    actor_email:   Optional[str]       = None
    actor_role:    Optional[str]       = None   # actor_role_snapshot at time of action
    actor_avatar:  Optional[str]       = None   # user_profiles.profile_picture_url

    created_at:    datetime


class ActivityFeedResponse(BaseModel):
    """Response for GET /workspace/activity-feed"""

    items:       List[ActivityFeedItem]
    total:       int
    page:        int
    limit:       int
    total_pages: int


# =============================================================================
# 7. CASE PIPELINE CHART
#    Powers the bar/funnel chart on ADMIN-10.
#    Always returns all 8 status buckets (count=0 when empty).
#    color_hex is used directly as chart bar fill by the frontend.
# =============================================================================

class PipelineStatusBucket(BaseModel):
    """One bar in the pipeline chart."""

    status:    str   # "draft"|"in_progress"|"action_needed"|…
    label:     str   # "In Progress"
    count:     int
    color_hex: str   # "#3B82F6"


class CasePipelineResponse(BaseModel):
    """Response for GET /workspace/case-pipeline"""

    buckets:                 List[PipelineStatusBucket]
    total:                   int
    previous_period_buckets: Optional[List[PipelineStatusBucket]] = None


# =============================================================================
# 8. PENDING DOCUMENTS QUEUE
#    Powers the "Documents Pending Review" widget on ADMIN-10.
#
#    visamodels.py CHANGES vs old models:
#      • Pending statuses: "pending_review" | "under_review"
#        (old: "uploaded" | "pending_review" — "uploaded" status no longer exists)
#      • file_size_bytes  replaces  file_size_kb
#      • file_type        replaces  file_format  (now String, not Enum)
#      • is_draft column REMOVED — no need to filter it out
# =============================================================================

class PendingDocumentItem(BaseModel):
    """One document card in the pending review queue."""

    id:                  uuid.UUID
    file_name:           str
    file_type:           Optional[str]  = None  # "pdf"|"jpg"|… — was file_format
    file_size_bytes:     Optional[int]  = None  # raw bytes — display: / 1048576 for MB
    status:              str                    # "pending_review"|"under_review"
    document_type:       str                    # "Valid Passport" — from document_types.name
    ocr_status:          str                    # ocr_status_enum value

    uploader_id:         uuid.UUID
    uploader_name:       str

    application_id:      Optional[uuid.UUID] = None
    application_number:  Optional[str]       = None

    uploaded_at:         datetime             # document.created_at


class PendingDocumentsResponse(BaseModel):
    """Response for GET /workspace/pending-documents"""

    items:       List[PendingDocumentItem]
    total:       int
    page:        int
    limit:       int
    total_pages: int


# =============================================================================
# 9. TEAM WORKLOAD PANEL
#    Powers the "Team" sidebar on ADMIN-10.
#
#    NEW in visamodels.py:
#      • attorney_profiles.profile_photo_url available for attorneys
#      • user_profiles.profile_picture_url used for all users (consistent)
#      • attorney_profiles.is_accepting_cases + max_active_cases exposed
# =============================================================================

class TeamMemberItem(BaseModel):
    """One team member card in the workload panel."""

    id:                     uuid.UUID
    first_name:             str
    last_name:              str
    email:                  str
    role:                   str              # "attorney"|"hr"|"app_admin"
    profile_picture_url:    Optional[str]  = None   # user_profiles.profile_picture_url

    # Attorney-only enrichment (from attorney_profiles) — null for hr/admin
    law_firm_name:          Optional[str]  = None
    is_accepting_cases:     Optional[bool] = None
    max_active_cases:       Optional[int]  = None

    # Computed workload
    active_case_count:      int
    pending_task_count:     int
    overdue_deadline_count: int             # due_date < now AND is_completed=False

    last_login_at:          Optional[datetime] = None
    is_online:              bool = False    # last_login_at within last 15 min


class TeamWorkloadResponse(BaseModel):
    """Response for GET /workspace/team"""

    items: List[TeamMemberItem]
    total: int


# =============================================================================
# 10. FULL DASHBOARD AGGREGATION
#     GET /workspace/dashboard — single call for full ADMIN-10 initial load.
#     All list sections capped at preview limits.
# =============================================================================

class WorkspaceDashboardResponse(BaseModel):
    """
    Response for GET /workspace/dashboard.
    One call — entire ADMIN-10 screen initial load.
    """

    # ── KPI cards ─────────────────────────────────────────────────────────────
    kpi:                  WorkspaceKPIResponse

    # ── Main panels ───────────────────────────────────────────────────────────
    recent_applications:  List[RecentApplicationItem]   # top 5
    my_tasks:             List[WorkspaceTaskItem]        # top 10 pending-first
    pending_documents:    List[PendingDocumentItem]      # top 5

    # ── Sidebar ───────────────────────────────────────────────────────────────
    upcoming_deadlines:   List[UpcomingDeadlineItem]     # top 5
    activity_feed:        List[ActivityFeedItem]         # top 10
    team:                 List[TeamMemberItem]           # all team members

    # ── Chart ─────────────────────────────────────────────────────────────────
    case_pipeline:        CasePipelineResponse

    # ── Meta ──────────────────────────────────────────────────────────────────
    generated_at:         datetime
    current_user_role:    str        # "app_admin"|"hr"|"attorney"
