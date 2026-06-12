// src/api/admin-dashboard.api.ts

import axios from "./axios";

// ── Types ──────────────────────────────────────────────────────────
export interface DashboardStats {
  totalUsers:    { value: number; trend: string; trendUp: boolean };
  activeCases:   { value: number; trend: string; trendUp: boolean };
  visaTypes:     { value: number; trend: string };
  documentTypes: { value: number; trend: string };
  aiAccuracy:    { value: number; trend: string; trendUp: boolean };
  pendingIssues: { value: number; trend: string };
}

export interface SystemStatus {
  status:    "operational" | "degraded" | "outage";
  label:     string;
  updatedAt: string;
}

export interface UptimeData {
  uptimePercent: number;
  chartData: { date: string; uptimeMinutes: number; downtimeMinutes: number }[];
}

export interface CaseVolumeData {
  chartData: { date: string; created: number; completed: number }[];
}

export interface NavTab {
  key:     string;
  label:   string;
  enabled: boolean;
}

export interface SystemLog {
  id:        string;
  timestamp: string;
  level:     "error" | "warn" | "info";
  message:   string;
}

// ── API calls ──────────────────────────────────────────────────────

/** GET /admin/dashboard/stats */
export const fetchDashboardStats = async (): Promise<DashboardStats> => {
  const res = await axios.get("/admin/dashboard/stats");
  return res.data.data;
};

/** GET /admin/dashboard/system-status */
export const fetchSystemStatus = async (): Promise<SystemStatus> => {
  const res = await axios.get("/admin/dashboard/system-status");
  return res.data.data;
};

/** GET /admin/dashboard/system-uptime */
export const fetchSystemUptime = async (): Promise<UptimeData> => {
  const res = await axios.get("/admin/dashboard/system-uptime");
  return res.data.data;
};

/** GET /admin/dashboard/case-processing-volume */
export const fetchCaseVolume = async (from: string, to: string): Promise<CaseVolumeData> => {
  const res = await axios.get("/admin/dashboard/case-processing-volume", { params: { from, to } });
  return res.data.data;
};

/** GET /admin/dashboard/navigation-tabs */
export const fetchNavTabs = async (): Promise<NavTab[]> => {
  const res = await axios.get("/admin/dashboard/navigation-tabs");
  return res.data.data.tabs;
};

/** GET /admin/system-logs */
export const fetchSystemLogs = async (params?: {
  level?: "error" | "warn" | "info";
  from?: string;
  to?: string;
  limit?: number;
}): Promise<{ logs: SystemLog[]; total: number }> => {
  const res = await axios.get("/admin/system-logs", { params });
  return res.data.data;
};
