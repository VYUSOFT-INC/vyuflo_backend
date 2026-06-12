// src/hooks/useDashboard.ts
// import { useState, useEffect, useCallback } from "react";
// import type { AxiosError } from "axios";
// import type { RecentLoginsResponse,DashboardResponse,DashboardCounts } from "../types/dashboard.types";
// import { getDashboard } from "../api/dashboard.api";
// import { getAdminCounts } from "../api/dashboard.api";
import { useState, useEffect, useCallback } from "react";
import type { AxiosError } from "axios";
import type {
  DashboardResponse,
  DashboardCounts,
  RecentLoginsResponse,
  RecentLoginUser,
} from "../../types/admin/dashboard.types";
import { getDashboard, getAdminCounts, getRecentLogins } from "../../api/admin/dashboard.api";
function extractMessage(e: unknown): string {
  const err = e as AxiosError<{ detail: string }>;
  return (
    err.response?.data?.detail ??
    (e instanceof Error ? e.message : "Something went wrong.")
  );
}

export function useDashboard() {
  const [data, setData]         = useState<DashboardResponse | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getDashboard());
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}


export function useAdminCounts() {
  const [data, setData]         = useState<DashboardCounts | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getAdminCounts());
    } catch (e) {
      setError(extractMessage(e));   // reuses the extractMessage already in the file
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}

export function useRecentLogins(limit: number, offset: number) {
  const [data, setData]         = useState<RecentLoginUser[]>([]);
  const [total, setTotal]       = useState(0);
  const [isLoading, setLoading] = useState(true);
  const [error, setError]       = useState<string | null>(null);
 
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res: RecentLoginsResponse = await getRecentLogins(limit, offset);
      const items = res.items ?? [];
      setData(items);
      setTotal(res.total ?? items.length);
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, [limit, offset]);
 
  useEffect(() => { void load(); }, [load]);
 
  return { data, total, isLoading, error, refetch: load };
}