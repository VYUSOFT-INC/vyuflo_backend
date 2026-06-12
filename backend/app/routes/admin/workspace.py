"""
workspace_router.py — API routes for ADMIN-10 Workspace Dashboard.

FILE LOCATION
    app/routers/workspace_router.py

CORRECTED FOR visamodels.py (57 tables)
    ✅ /upcoming-deadlines : urgency query param replaces priority
                             enum: critical | high | medium | low
    ✅ /activity-feed      : event_type query param REMOVED
                             (AuditLog.event_type column gone in new models)
    ✅ All docstrings updated to reflect new enum values

REGISTER IN main.py
    from app.routers.workspace_router import workspace_router
    app.include_router(workspace_router, prefix="/api/v1")

ENDPOINTS
    GET  /workspace/dashboard              full aggregated initial load
    GET  /workspace/kpi                    4 KPI cards (poll every 60 s)
    GET  /workspace/recent-applications    paginated + search + status filter
    GET  /workspace/my-tasks               task checklist, completed filter
    GET  /workspace/upcoming-deadlines     deadline sidebar, urgency + window
    GET  /workspace/activity-feed          audit event stream, severity + resource_type
    GET  /workspace/case-pipeline          bar chart data (8 status buckets)
    GET  /workspace/pending-documents      doc review queue, paginated
    GET  /workspace/team                   team workload panel

⚠️  ADJUST THESE TWO IMPORTS to match your project layout:
    get_db           → yields AsyncSession
    get_current_user → returns authenticated User object (must have .id)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_permissions import get_current_user, get_db
from app.models.visamodels import User
from app.services.admin import workspace_service
from app.schemas.admin.workspace import (
    ActivityFeedResponse,
    CasePipelineResponse,
    MyTasksResponse,
    PendingDocumentsResponse,
    RecentApplicationsResponse,
    TeamWorkloadResponse,
    UpcomingDeadlinesResponse,
    WorkspaceDashboardResponse,
    WorkspaceKPIResponse,
)

workspace_router = APIRouter(tags=["Workspace Dashboard"])


# ===========================================================================
# FULL DASHBOARD — single aggregated call for initial page load
# ===========================================================================

@workspace_router.get(
    "/workspace/dashboard",
    response_model=WorkspaceDashboardResponse,
    summary="ADMIN-10 — full workspace dashboard (initial page load)",
    description=(
        "Single aggregated response for the entire Workspace Dashboard screen.\n\n"
        "Returns: KPIs · recent applications (top 5) · pending tasks (top 10 incomplete) · "
        "upcoming deadlines (top 5 active) · activity feed (top 10) · "
        "case pipeline chart · pending documents (top 5) · team workload.\n\n"
        "**Use individual endpoints for pagination and live widget refresh.**"
    ),
)
async def get_workspace_dashboard(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await workspace_service.service_get_workspace_dashboard(db, current_user.id)


# ===========================================================================
# KPI SUMMARY CARDS
# ===========================================================================

@workspace_router.get(
    "/workspace/kpi",
    response_model=WorkspaceKPIResponse,
    summary="KPI summary cards — total apps, active cases, pending tasks, overdue deadlines",
    description=(
        "Lightweight endpoint for the four stat cards at the top of ADMIN-10.\n\n"
        "**Recommended poll interval: 60 seconds** — keeps cards fresh without "
        "reloading the full dashboard.\n\n"
        "**Overdue deadlines** are computed as: "
        "`is_completed=False AND is_dismissed=False AND due_date < now`\n\n"
        "Includes optional `*_delta_pct` badges (week-over-week) when sufficient data exists."
    ),
)
async def get_workspace_kpi(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await workspace_service.service_get_workspace_kpi(db, current_user.id)


# ===========================================================================
# RECENT APPLICATIONS TABLE
# ===========================================================================

@workspace_router.get(
    "/workspace/recent-applications",
    response_model=RecentApplicationsResponse,
    summary="Recent applications — paginated table with search and status filter",
    description=(
        "Full paginated applications table for the main panel on ADMIN-10.\n\n"
        "**Filters:**\n"
        "- `status` → exact match: `draft | in_progress | action_needed | "
        "rfe_response | submitted | approved | rejected | withdrawn`\n"
        "- `search` → case-insensitive match on application number, "
        "applicant first/last name, email\n\n"
        "**Sort:** `updated_at DESC` — most recently touched first.\n\n"
        "**Scoping:** `app_admin` sees all; `hr` → own assigned cases; "
        "`attorney` → own assigned cases."
    ),
)
async def get_recent_applications(
    page:   int           = Query(1,   ge=1,          description="Page number (1-based)"),
    limit:  int           = Query(10,  ge=1,  le=100, description="Items per page"),
    status: Optional[str] = Query(
        None,
        description=(
            "Filter by status: "
            "draft | in_progress | action_needed | rfe_response | "
            "submitted | approved | rejected | withdrawn"
        ),
    ),
    search: Optional[str] = Query(
        None, min_length=1, max_length=100,
        description="Search by application number, applicant name or email",
    ),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await workspace_service.service_get_recent_applications(
        db,
        current_user_id=current_user.id,
        page=page,
        limit=limit,
        status_filter=status,
        search=search,
    )


# ===========================================================================
# MY TASKS CHECKLIST
# ===========================================================================

@workspace_router.get(
    "/workspace/my-tasks",
    response_model=MyTasksResponse,
    summary="My tasks — checklist of incomplete tasks on current user's assigned cases",
    description=(
        "Returns `application_tasks` rows from all applications assigned to "
        "the current user.\n\n"
        "**completed filter:**\n"
        "- omit → all tasks (pending + done)\n"
        "- `false` → pending only *(default for the widget)*\n"
        "- `true` → completed only\n\n"
        "**Sort:** incomplete first, then `created_at ASC`.\n\n"
        "Response always includes `completed_count` and `pending_count` "
        "for the progress bar, regardless of which filter is applied."
    ),
)
async def get_my_tasks(
    page:      int            = Query(1,   ge=1,          description="Page number"),
    limit:     int            = Query(20,  ge=1,  le=100, description="Items per page"),
    completed: Optional[bool] = Query(
        None,
        description="true = completed only | false = pending only | omit = all",
    ),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await workspace_service.service_get_my_tasks(
        db,
        current_user_id=current_user.id,
        page=page,
        limit=limit,
        completed=completed,
    )


# ===========================================================================
# UPCOMING DEADLINES SIDEBAR
# ===========================================================================

@workspace_router.get(
    "/workspace/upcoming-deadlines",
    response_model=UpcomingDeadlinesResponse,
    summary="Upcoming deadlines — urgency-coloured sidebar list",
    description=(
        "Returns active (not completed, not dismissed) deadlines within "
        "the next `days_ahead` days. "
        "Overdue deadlines (`due_date < now`) are **always included** "
        "regardless of the window.\n\n"
        "**Overdue logic** (no status column in visamodels.py):\n"
        "`is_completed=False AND is_dismissed=False AND due_date < now`\n\n"
        "**Urgency colour mapping:**\n"
        "- `critical` → red badge + red due-date text\n"
        "- `high`     → amber badge\n"
        "- `medium`   → blue badge\n"
        "- `low`      → grey badge\n\n"
        "`days_until_due` is **negative** for overdue deadlines.\n\n"
        "**Sort:** `due_date ASC` — most urgent first."
    ),
)
async def get_upcoming_deadlines(
    page:       int           = Query(1,  ge=1,          description="Page number"),
    limit:      int           = Query(10, ge=1,  le=100, description="Items per page"),
    urgency:    Optional[str] = Query(
        None,
        description="Filter by urgency: critical | high | medium | low",
    ),
    days_ahead: int           = Query(
        30, ge=1, le=365,
        description="Show deadlines due within this many days (overdue always included)",
    ),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await workspace_service.service_get_upcoming_deadlines(
        db,
        current_user_id=current_user.id,
        page=page,
        limit=limit,
        urgency=urgency,
        days_ahead=days_ahead,
    )


# ===========================================================================
# ACTIVITY FEED
# ===========================================================================

@workspace_router.get(
    "/workspace/activity-feed",
    response_model=ActivityFeedResponse,
    summary="Team activity feed — recent audit log events",
    description=(
        "Recent actions by the team sourced from `audit_logs`: "
        "status changes, document uploads, role assignments, payments, etc.\n\n"
        "**NOTE:** `event_type` filter has been removed — "
        "the `event_type` column no longer exists in `visamodels.py`.\n\n"
        "**Available filters:** `severity`, `resource_type`\n\n"
        "**Scoping:**\n"
        "- `app_admin` → all events system-wide\n"
        "- `hr / attorney` → events where `actor = current_user` OR "
        "`resource_type = application` and resource is one of their assigned cases\n\n"
        "**Sort:** `created_at DESC` — newest first."
    ),
)
async def get_activity_feed(
    page:          int           = Query(1,  ge=1,          description="Page number"),
    limit:         int           = Query(20, ge=1,  le=100, description="Items per page"),
    severity:      Optional[str] = Query(
        None,
        description="Filter by severity: info | warning | critical",
    ),
    resource_type: Optional[str] = Query(
        None,
        description=(
            "Filter by resource type: "
            "application | document | user | payment | "
            "subscription | support_ticket | role"
        ),
    ),
    # event_type parameter REMOVED — AuditLog.event_type column gone in visamodels.py
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await workspace_service.service_get_activity_feed(
        db,
        current_user_id=current_user.id,
        page=page,
        limit=limit,
        severity=severity,
        resource_type=resource_type,
    )


# ===========================================================================
# CASE PIPELINE CHART
# ===========================================================================

@workspace_router.get(
    "/workspace/case-pipeline",
    response_model=CasePipelineResponse,
    summary="Case pipeline chart — application counts by status (bar chart data)",
    description=(
        "Returns exactly **8 buckets** — one per application status. "
        "Buckets with `count=0` are always included so chart axes stay stable.\n\n"
        "Each bucket includes `color_hex` used directly as the bar fill colour.\n\n"
        "**Scoped** to the current user's assigned cases (unless `app_admin`)."
    ),
)
async def get_case_pipeline(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await workspace_service.service_get_case_pipeline(db, current_user.id)


# ===========================================================================
# PENDING DOCUMENTS QUEUE
# ===========================================================================

@workspace_router.get(
    "/workspace/pending-documents",
    response_model=PendingDocumentsResponse,
    summary="Pending documents — files awaiting HR/attorney review",
    description=(
        "Documents with `status IN (pending_review, under_review)` "
        "that need staff review.\n\n"
        "**NOTE vs old models:**\n"
        "- `uploaded` status no longer exists in `visamodels.py`\n"
        "- `file_size_bytes` replaces `file_size_kb` (now raw bytes)\n"
        "- `file_type` (String) replaces `file_format` (Enum)\n"
        "- `is_draft` filter removed (column gone)\n\n"
        "**Scoped** to documents linked to the current user's assigned applications.\n\n"
        "**Sort:** `created_at DESC` — newest upload first."
    ),
)
async def get_pending_documents(
    page:  int = Query(1,  ge=1,          description="Page number"),
    limit: int = Query(10, ge=1,  le=100, description="Items per page"),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await workspace_service.service_get_pending_documents(
        db,
        current_user_id=current_user.id,
        page=page,
        limit=limit,
    )


# ===========================================================================
# TEAM WORKLOAD PANEL
# ===========================================================================

@workspace_router.get(
    "/workspace/team",
    response_model=TeamWorkloadResponse,
    summary="Team workload — attorneys and HR staff with live case metrics",
    description=(
        "Returns active `attorney` and `hr` (+ `app_admin`) users with workload:\n"
        "- `active_case_count` — cases in `in_progress / action_needed / rfe_response`\n"
        "- `pending_task_count` — incomplete tasks on assigned cases\n"
        "- `overdue_deadline_count` — "
        "`due_date < now AND is_completed=False AND is_dismissed=False`\n"
        "- `is_online` — `True` if `last_login_at` within last 15 minutes\n\n"
        "**Attorney enrichment** (from `attorney_profiles` — new in visamodels.py):\n"
        "- `law_firm_name`, `is_accepting_cases`, `max_active_cases`\n\n"
        "**Visibility:**\n"
        "- `app_admin` → full team\n"
        "- `hr` → attorneys + HR\n"
        "- `attorney` → themselves only"
    ),
)
async def get_team_workload(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await workspace_service.service_get_team_workload(db, current_user.id)
