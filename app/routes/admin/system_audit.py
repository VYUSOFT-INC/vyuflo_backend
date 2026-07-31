"""
app/routes/system_audit.py

Mount in main.py:
    from app.routes.system_audit import system_audit_router
    app.include_router(system_audit_router, prefix="/api/v1", tags=["Admin — System Audit Logs"])
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User
from app.schemas.admin.system_audit import (
    ActivityTimelineResponse,
    AuditDashboardFullResponse,
    AuditDashboardKPIResponse,
    AuditLogListResponse,
    EventTypeDistributionResponse,
    SecurityEventsResponse,
    TimelinePeriod,
    TopUserActivitiesResponse,
)
from app.services.admin import system_audit_service

system_audit_router = APIRouter()


@system_audit_router.get("/admin/audit/dashboard/full", response_model=AuditDashboardFullResponse)
async def get_full_dashboard(
    period: TimelinePeriod = Query("7days"),
    year:   Optional[int]  = Query(None),
    month:  Optional[int]  = Query(None, ge=1, le=12),
    db:     AsyncSession   = Depends(get_db),
    current_user: User     = Depends(get_current_user),
):
    return await system_audit_service.service_get_full_audit_dashboard(db, period, year, month)


@system_audit_router.get("/admin/audit/dashboard", response_model=AuditDashboardKPIResponse)
async def get_audit_kpis(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await system_audit_service.service_get_audit_kpis(db)


@system_audit_router.get("/admin/audit/timeline", response_model=ActivityTimelineResponse)
async def get_activity_timeline(
    period: TimelinePeriod = Query("7days"),
    year:   Optional[int]  = Query(None),
    month:  Optional[int]  = Query(None, ge=1, le=12),
    db:     AsyncSession   = Depends(get_db),
    current_user: User     = Depends(get_current_user),
):
    return await system_audit_service.service_get_activity_timeline(db, period, year, month)


@system_audit_router.get("/admin/audit/event-types", response_model=EventTypeDistributionResponse)
async def get_event_types(
    period: TimelinePeriod = Query("7days"),
    year:   Optional[int]  = Query(None),
    month:  Optional[int]  = Query(None, ge=1, le=12),
    db:     AsyncSession   = Depends(get_db),
    current_user: User     = Depends(get_current_user),
):
    return await system_audit_service.service_get_event_type_distribution(db, period, year, month)


@system_audit_router.get("/admin/audit/top-users", response_model=TopUserActivitiesResponse)
async def get_top_users(
    period:      TimelinePeriod = Query("7days"),
    role_filter: str            = Query("all", description="all | app_admin | hr | employee | attorney"),
    year:        Optional[int]  = Query(None),
    month:       Optional[int]  = Query(None, ge=1, le=12),
    limit:       int            = Query(10, ge=1, le=50),
    db:          AsyncSession   = Depends(get_db),
    current_user: User          = Depends(get_current_user),
):
    return await system_audit_service.service_get_top_user_activities(db, period, role_filter, year, month, limit)


@system_audit_router.get("/admin/audit/security-events", response_model=SecurityEventsResponse)
async def get_security_events(
    period: TimelinePeriod = Query("7days"),
    year:   Optional[int]  = Query(None),
    month:  Optional[int]  = Query(None, ge=1, le=12),
    db:     AsyncSession   = Depends(get_db),
    current_user: User     = Depends(get_current_user),
):
    return await system_audit_service.service_get_security_events(db, period, year, month)


@system_audit_router.get("/admin/audit/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    period:     TimelinePeriod = Query("7days"),
    event_type: Optional[str]  = Query(None),
    action:     Optional[str]  = Query(None),
    page:       int            = Query(1, ge=1),
    page_size:  int            = Query(20, ge=1, le=100),
    year:       Optional[int]  = Query(None),
    month:      Optional[int]  = Query(None, ge=1, le=12),
    db:         AsyncSession   = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await system_audit_service.service_list_audit_logs(db, page, page_size, event_type, action, None, period, year, month)


@system_audit_router.get("/admin/audit/export")
async def export_audit_logs(
    period:     TimelinePeriod = Query("7days"),
    event_type: Optional[str]  = Query(None),
    year:       Optional[int]  = Query(None),
    month:      Optional[int]  = Query(None, ge=1, le=12),
    db:         AsyncSession   = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    from datetime import datetime, timezone
    csv_content = await system_audit_service.service_export_audit_logs(db, period, year, month, event_type)
    filename    = f"audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
