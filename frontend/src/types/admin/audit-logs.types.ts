// src/types/audit-logs.types.ts
//
// Types matching the System Audit Logs swagger schemas.

/* ───── Shared ──────────────────────────────────────────────────────── */

export type AuditPeriod = '24h' | '7days' | '30days' | '90days';

/* ───── KPI section ─────────────────────────────────────────────────── */

export interface AuditKpiMetric {
  value_display:  string;       // backend formats it (e.g., "12,847", "99.98%")
  delta_display:  string;       // e.g., "+12.5%"
  delta_positive: boolean;
  period_label:   string;       // "24h"
}

export interface AuditKpiSection {
  total_events:    AuditKpiMetric;
  user_actions:    AuditKpiMetric;
  security_events: AuditKpiMetric;
  failed_logins:   AuditKpiMetric;
  system_uptime:   AuditKpiMetric;
  all_systems_ok:  boolean;
}

/* ───── Activity Timeline (line chart) ──────────────────────────────── */

export interface TimelineDataPoint {
  label:       string;     // "Jan 10"
  date_key:    string;     // ISO date or YYYY-MM-DD
  event_count: number;
}

export interface AuditTimelineSection {
  data_points:  TimelineDataPoint[];
  period:       AuditPeriod | string;
  year:         number;
  month:        number;
  total_events: number;
  y_axis_max:   number;
}

/* ───── Event Types Distribution (donut) ────────────────────────────── */

export interface EventTypeSlice {
  event_type: string;     // identifier like "user_login"
  label:      string;     // display label
  count:      number;
  percentage: number;
  color:      string;     // hex
}

export interface EventTypesSection {
  slices:       EventTypeSlice[];
  total_events: number;
  period:       AuditPeriod | string;
}

/* ───── Top User Activities (bar chart / list) ──────────────────────── */

export interface TopUser {
  user_id:         string;
  user_name:       string;
  user_email:      string;
  avatar_initials: string;
  role:            string;
  action_count:    number;
  last_action_at:  string;   // ISO timestamp
}

export interface TopUsersSection {
  users:       TopUser[];
  period:      AuditPeriod | string;
  role_filter: string;       // "all" | "admin" | etc.
  total_users: number;
}

/* ───── Security Events by Type (donut) ─────────────────────────────── */

export interface SecurityEventSlice {
  security_event_type: string;
  label:               string;
  count:               number;
  percentage:          number;
  color:               string;
}

export interface SecurityEventsSection {
  slices:      SecurityEventSlice[];
  total_count: number;
  period:      AuditPeriod | string;
}

/* ───── Audit Logs Table (paginated) ────────────────────────────────── */

export interface AuditLogItem {
  id:                  string;
  actor_id:            string;
  actor_name:          string;
  actor_email:         string;
  actor_type:          string;       // "user" | "system" | etc.
  actor_role:          string;
  event_type:          string;
  event_type_label:    string;
  action:              string;
  action_label:        string;
  resource:            string;
  resource_id:         string;
  description:         string;
  security_event_type: string | null;
  ip_address:          string;
  extra_metadata:      string | null;
  created_at:          string;       // ISO timestamp
}

export interface AuditLogsListSection {
  items:       AuditLogItem[];
  total:       number;
  page:        number;
  page_size:   number;
  total_pages: number;
}

/* ───── Combined Dashboard Response ─────────────────────────────────── */

export interface AuditDashboardResponse {
  kpi:          AuditKpiSection;
  timeline:     AuditTimelineSection;
  event_types:  EventTypesSection;
  top_users:    TopUsersSection;
  security:     SecurityEventsSection;
  generated_at: string;
}

/* ───── Request params ──────────────────────────────────────────────── */

export interface AuditBaseParams {
  period?: AuditPeriod | string;
  year?:   number;
  month?:  number;
}

export interface TopUsersParams extends AuditBaseParams {
  role_filter?: string;   // default "all"
  limit?:       number;   // default 10
}

export interface AuditLogsListParams extends AuditBaseParams {
  page?:                number;
  page_size?:           number;
  actor_id?:            string;
  event_type?:          string;
  security_event_type?: string;
  q?:                   string;       // free-text search
}