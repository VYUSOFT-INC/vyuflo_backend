"""
app/schemas/system_audit.py — Fixed to match system_audit_service.py exactly.

Changes from old schema:
  ✅ AuditDashboardKPIResponse — replaced user_actions/system_uptime/all_systems_ok
                                  with active_users (matches service)
  ✅ TimelineDataPoint         — replaced label/date_key with date/login_count
                                  (matches service)
  ✅ ActivityTimelineResponse  — removed total_events/y_axis_max (service doesn't send)
                                  added login_count field
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

TimelinePeriod = Literal["7days", "30days", "month", "year"]


# ===========================================================================
# KPI CARDS
# ===========================================================================

class AuditKPICard(BaseModel):
    value_display:  str
    delta_display:  Optional[str]  = None
    delta_positive: Optional[bool] = None
    period_label:   str            = "24h"


class AuditDashboardKPIResponse(BaseModel):
    """
    Matches service_get_audit_kpis() exactly.
    Fields: total_events, security_events, active_users, failed_logins
    """
    total_events:    AuditKPICard
    security_events: AuditKPICard
    active_users:    AuditKPICard   # ✅ was user_actions — fixed
    failed_logins:   AuditKPICard
    # removed: system_uptime, all_systems_ok — service doesn't return these


# ===========================================================================
# TIMELINE
# ===========================================================================

class TimelineDataPoint(BaseModel):
    """
    Matches service_get_activity_timeline() exactly.
    Fields: date, event_count, login_count
    """
    date:        str   # ✅ was label/date_key — fixed
    event_count: int
    login_count: int = 0  # ✅ added — service sends this


class ActivityTimelineResponse(BaseModel):
    data_points: List[TimelineDataPoint]
    period:      TimelinePeriod
    year:        Optional[int] = None
    month:       Optional[int] = None
    # removed: total_events, y_axis_max — service doesn't send these


# ===========================================================================
# EVENT TYPE DISTRIBUTION
# ===========================================================================

class EventTypeSlice(BaseModel):
    event_type:  str
    label:       str
    count:       int
    percentage:  float
    color:       str


class EventTypeDistributionResponse(BaseModel):
    slices:       List[EventTypeSlice]
    total_events: int
    period:       TimelinePeriod = "7days"


# ===========================================================================
# TOP USER ACTIVITIES
# ===========================================================================

class TopUserActivity(BaseModel):
    user_id:         uuid.UUID
    user_name:       str
    user_email:      str
    avatar_initials: str
    role:            str
    action_count:    int
    last_action_at:  Optional[datetime] = None


class TopUserActivitiesResponse(BaseModel):
    users:       List[TopUserActivity]
    period:      TimelinePeriod
    role_filter: str = "all"
    total_users: int = 0


# ===========================================================================
# SECURITY EVENTS
# ===========================================================================

class SecurityEventSlice(BaseModel):
    security_event_type: str
    label:               str
    count:               int
    percentage:          float
    color:               str


class SecurityEventsResponse(BaseModel):
    slices:      List[SecurityEventSlice]
    total_count: int
    period:      TimelinePeriod


# ===========================================================================
# AUDIT LOG LIST
# ===========================================================================

class AuditLogRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                  uuid.UUID
    actor_id:            Optional[uuid.UUID]
    actor_name:          Optional[str]
    actor_email:         Optional[str]
    actor_type:          str
    actor_role:          Optional[str]
    event_type:          str
    event_type_label:    str
    action:              str
    action_label:        str
    resource:            Optional[str]
    resource_id:         Optional[str]
    description:         Optional[str]
    security_event_type: Optional[str]
    ip_address:          Optional[str]
    extra_metadata:      Optional[str] = None
    created_at:          datetime


class AuditLogListResponse(BaseModel):
    items:       List[AuditLogRow]
    total:       int
    page:        int = 1
    page_size:   int = 20
    total_pages: int = 1


# ===========================================================================
# FULL DASHBOARD
# ===========================================================================

class AuditDashboardFullResponse(BaseModel):
    kpi:          AuditDashboardKPIResponse
    timeline:     ActivityTimelineResponse
    event_types:  EventTypeDistributionResponse
    top_users:    TopUserActivitiesResponse
    security:     SecurityEventsResponse
    generated_at: datetime
