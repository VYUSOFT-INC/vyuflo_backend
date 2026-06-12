// src/hooks/useDashboard.ts
import { useState, useEffect, useCallback } from "react";
import type { AxiosError } from "axios";
import type { DashboardResponse } from "../../types/employee/dashboard.types";
import { getDashboard } from "../../api/employee/dashboard.api";

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