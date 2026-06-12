// src/api/dashboard.api.ts
import axios from "../axios";
import type { RecentLoginsResponse,DashboardCounts,DashboardResponse, ActivityItem, ProfileReadiness } from "../../types/admin/dashboard.types";

export async function getDashboard(): Promise<DashboardResponse> {
  const res = await axios.get("/dashboard");
  return res.data;
}
// ── NEW ──
export const getAdminCounts = async (): Promise<DashboardCounts> => {
  const res = await axios.get("/dashboard/counts");
  return res.data;
};

export async function getDashboardActivity(): Promise<ActivityItem[]> {
  const res = await axios.get("/dashboard/activity");
  return Array.isArray(res.data) ? res.data : res.data.items ?? [];
}

export async function getProfileReadiness(): Promise<ProfileReadiness> {
  const res = await axios.get("/dashboard/profile-readiness");
  return res.data;
}

// ── NEW: GET /api/v1/dashboard/recent-logins?limit=&offset= ───────
// Returns: { items: RecentLoginUser[], total?: number }
 
export const getRecentLogins = async (
  limit: number,
  offset: number
): Promise<RecentLoginsResponse> => {
  const res = await axios.get("/dashboard/recent-logins", {
    params: { limit, offset },
  });
  return res.data;
};