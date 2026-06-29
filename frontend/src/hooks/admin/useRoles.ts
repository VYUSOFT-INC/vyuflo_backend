// src/hooks/useRoles.ts
import { useState, useEffect, useCallback } from "react";
import type { AxiosError } from "axios";
import type { Role, PermissionItem } from "../../types/admin/roles.types";
import { fetchRoles, fetchAllPermissions } from "../../api/admin/roles.api";

function extractMessage(e: unknown): string {
  const err = e as AxiosError<{ detail: string }>;
  return (
    err.response?.data?.detail ??
    (e instanceof Error ? e.message : "Something went wrong. Please try again.")
  );
}

// ── List all roles ──────────────────────────────────────────────────────────────
export function useRoles() {
  const [data, setData]         = useState<Role[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchRoles();
      setData(res.items ?? []);
    } catch (e) {
      setError(extractMessage(e));
      setData([]); // never leave it undefined
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}

// ── Full permission master list (fetched once, reused for every role) ───────────
export function usePermissions() {
  const [data, setData]         = useState<PermissionItem[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAllPermissions();
      setData(res.items ?? []);
    } catch (e) {
      setError(extractMessage(e));
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}