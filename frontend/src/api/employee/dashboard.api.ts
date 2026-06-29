// src/api/dashboard.api.ts
import axios from "../axios";
import type { DashboardResponse, ActivityItem, ProfileReadiness } from "../../types/employee/dashboard.types";

export async function getDashboard(): Promise<DashboardResponse> {
  const res = await axios.get("/dashboard");
  return res.data;
}

export async function getDashboardActivity(): Promise<ActivityItem[]> {
  const res = await axios.get("/dashboard/activity");
  return Array.isArray(res.data) ? res.data : res.data.items ?? [];
}

export async function getProfileReadiness(): Promise<ProfileReadiness> {
  const res = await axios.get("/dashboard/profile-readiness");
  return res.data;
}