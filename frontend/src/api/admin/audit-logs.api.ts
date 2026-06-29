// src/api/audit-logs.api.ts
//
// Follows the same pattern as src/api/auth.api.ts — uses the configured axios
// instance from ./axios (whose baseURL already includes /api/v1).
//
// 👉 Endpoint URLs confirmed from Swagger UI screenshots:
//    /admin/audit/event-types      ✅
//    /admin/audit/top-users        ✅
//    /admin/audit/security-events  ✅
//    /admin/audit/logs             ✅
//    /admin/audit/export           ✅
//    The dashboard/kpi/timeline URLs below are best guesses — verify and
//    edit AUDIT_PATHS if your Swagger differs.

import axios from '../axios';
import type {
  AuditDashboardResponse,
  AuditKpiSection,
  AuditTimelineSection,
  EventTypesSection,
  TopUsersSection,
  SecurityEventsSection,
  AuditLogsListSection,
  AuditBaseParams,
  TopUsersParams,
  AuditLogsListParams,
} from '../../types/admin/audit-logs.types';

// ── Endpoint paths (single source of truth) ──────────────────────────────────
// ✅ All URLs verified against the Swagger UI under "System Audit".
export const AUDIT_PATHS = {
  dashboard:      '/admin/audit/dashboard/full',   // combined (Get Full Dashboard)
  kpi:            '/admin/audit/dashboard',        // KPI tiles  (Get Audit Kpis)
  timeline:       '/admin/audit/timeline',         // Activity Timeline
  eventTypes:     '/admin/audit/event-types',
  topUsers:       '/admin/audit/top-users',
  securityEvents: '/admin/audit/security-events',
  logs:           '/admin/audit/logs',
  exportLogs:     '/admin/audit/export',
} as const;

// ── Audit API ────────────────────────────────────────────────────────────────

export const auditApi = {
  /** KPI tiles (Total Events, User Actions, Security Events, Failed Logins, System Uptime). */
  getKpi: async (params: AuditBaseParams = {}): Promise<AuditKpiSection> => {
    const res = await axios.get(AUDIT_PATHS.kpi, { params });
    return res.data;
  },

  /** Activity Timeline line chart. */
  getTimeline: async (
    params: AuditBaseParams = {},
  ): Promise<AuditTimelineSection> => {
    const res = await axios.get(AUDIT_PATHS.timeline, { params });
    return res.data;
  },

  /** Event Types Distribution donut chart. */
  getEventTypes: async (
    params: AuditBaseParams = {},
  ): Promise<EventTypesSection> => {
    const res = await axios.get(AUDIT_PATHS.eventTypes, { params });
    return res.data;
  },

  /** Top User Activities bar chart / list. */
  getTopUsers: async (
    params: TopUsersParams = {},
  ): Promise<TopUsersSection> => {
    const res = await axios.get(AUDIT_PATHS.topUsers, {
      params: { role_filter: 'all', limit: 10, ...params },
    });
    return res.data;
  },

  /** Security Events by Type donut. */
  getSecurityEvents: async (
    params: AuditBaseParams = {},
  ): Promise<SecurityEventsSection> => {
    const res = await axios.get(AUDIT_PATHS.securityEvents, { params });
    return res.data;
  },

  /** Paginated audit logs table. */
  getLogs: async (
    params: AuditLogsListParams = {},
  ): Promise<AuditLogsListSection> => {
    const res = await axios.get(AUDIT_PATHS.logs, {
      params: { page: 1, page_size: 20, ...params },
    });
    return res.data;
  },

  /**
   * Combined dashboard endpoint — returns kpi + timeline + event_types +
   * top_users + security in one go. If your backend doesn't expose this,
   * use `getAllParallel` below which fans out individual endpoints.
   */
  getDashboard: async (
    params: AuditBaseParams = {},
  ): Promise<AuditDashboardResponse> => {
    const res = await axios.get(AUDIT_PATHS.dashboard, { params });
    return res.data;
  },

  /**
   * Parallel fan-out fallback — useful if the combined `dashboard` endpoint
   * isn't available. Uses Promise.allSettled so one broken endpoint doesn't
   * kill the whole dashboard.
   */
  getAllParallel: async (
    params: AuditBaseParams = {},
  ): Promise<AuditDashboardResponse> => {
    const [kpiR, timelineR, eventTypesR, topUsersR, securityR] =
      await Promise.allSettled([
        auditApi.getKpi(params),
        auditApi.getTimeline(params),
        auditApi.getEventTypes(params),
        auditApi.getTopUsers(params),
        auditApi.getSecurityEvents(params),
      ]);

    [
      ['kpi',         kpiR],
      ['timeline',    timelineR],
      ['event_types', eventTypesR],
      ['top_users',   topUsersR],
      ['security',    securityR],
    ].forEach(([name, result]) => {
      if ((result as PromiseSettledResult<unknown>).status === 'rejected') {
        // eslint-disable-next-line no-console
        console.warn(
          `[auditApi] ${name as string} endpoint failed:`,
          (result as PromiseRejectedResult).reason,
        );
      }
    });

    return {
      kpi:          kpiR.status        === 'fulfilled' ? kpiR.value        : (null as unknown as AuditKpiSection),
      timeline:     timelineR.status   === 'fulfilled' ? timelineR.value   : (null as unknown as AuditTimelineSection),
      event_types:  eventTypesR.status === 'fulfilled' ? eventTypesR.value : (null as unknown as EventTypesSection),
      top_users:    topUsersR.status   === 'fulfilled' ? topUsersR.value   : (null as unknown as TopUsersSection),
      security:     securityR.status   === 'fulfilled' ? securityR.value   : (null as unknown as SecurityEventsSection),
      generated_at: new Date().toISOString(),
    };
  },

  /**
   * Export Audit Logs — backend returns CSV/text.
   * Triggers a browser download client-side.
   */
  exportLogs: async (params: AuditBaseParams = {}): Promise<Blob> => {
    const res = await axios.get(AUDIT_PATHS.exportLogs, {
      params,
      responseType: 'blob',
    });
    return res.data as Blob;
  },
};

/** Helper used by the Export Logs button. */
export async function downloadAuditExport(
  params: AuditBaseParams = {},
): Promise<void> {
  const blob = await auditApi.exportLogs(params);
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}