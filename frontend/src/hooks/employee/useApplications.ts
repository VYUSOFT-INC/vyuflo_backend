// src/hooks/useApplications.ts
import { useState, useEffect, useCallback } from "react";
import type { AxiosError } from "axios";
import type {
  Application,
  ApplicationListResponse,
  ApplicationStatus,
  StatusHistory,
  Task,
  VisaType,
} from "../../types/employee/application.types";
import {
  listApplications,
  getApplication,
  listTasks,
  listStatusHistory,
  listVisaTypes,
} from "../../api/employee/applications.api";

function extractMessage(e: unknown): string {
  const err = e as AxiosError<{ detail: string }>;
  return (
    err.response?.data?.detail ??
    (e instanceof Error ? e.message : "Something went wrong. Please try again.")
  );
}

// ── Map backend task shape → frontend Task shape ──────────────────────────────
// FIX 1 — parameter typed as `unknown` then cast inside, not as Record<string, unknown>
// This matches what Array.map passes: (value: unknown, index: number, array: unknown[])
function mapTask(raw: unknown): Task {
  const t = raw as Record<string, unknown>;   // safe cast inside
  return {
    id:             t.id             as string,
    application_id: t.application_id as string,
    name:           (t.task_name ?? t.name) as string,   // backend sends task_name
    description:    t.description    as string | undefined,
    sort_order:     (t.sort_order    as number) ?? 0,
    is_completed:   t.is_completed   as boolean,
    completed_at:   t.completed_at   as string | undefined,
    completed_by:   t.completed_by   as string | undefined,
    document_id:          t.document_id          as string | undefined,
    document_name:        t.document_name        as string | undefined,
    document_size_bytes:  t.document_size_bytes  as number | undefined,
    document_uploaded_at: t.document_uploaded_at as string | undefined,
    created_at:     t.created_at     as string,
    updated_at:     t.updated_at     as string,
  };
}

// ── List all applications + KPI ───────────────────────────────────────────────
export function useApplications(params?: {
  status?:       ApplicationStatus;
  visa_type_id?: string;
  limit?:        number;
  offset?:       number;
}) {
  const [data, setData]         = useState<ApplicationListResponse | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const key = JSON.stringify(params);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listApplications(params);
      setData(result);
    } catch (e) {
      console.error("Applications API error:", e);
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}

// ── Single application ────────────────────────────────────────────────────────
export function useApplication(id: string | undefined) {
  const [data, setData]         = useState<Application | null>(null);
  const [isLoading, setLoading] = useState(!!id);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      setData(await getApplication(id));
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}

// ── Tasks checklist ───────────────────────────────────────────────────────────
export function useApplicationTasks(applicationId: string | undefined) {
  const [data, setData]         = useState<Task[] | null>(null);
  const [isLoading, setLoading] = useState(!!applicationId);
  const [error, setError]       = useState<string | null>(null);

  // FIX 2 — removed unused `applicationId` variable in the inner scope.
  // useCallback dependency is the outer `applicationId` parameter directly.
  const load = useCallback(async () => {
    if (!applicationId) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const raw = await listTasks(applicationId);
      // raw is unknown[] from the API — map each item through mapTask
      const items: unknown[] = Array.isArray(raw)
        ? raw
        : ((raw as { items?: unknown[] }).items ?? []);
      setData(items.map(mapTask));
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, [applicationId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { void load(); }, [load]);

  return { data, setData, isLoading, error, refetch: load };
}

// ── Status history timeline ───────────────────────────────────────────────────
export function useStatusHistory(applicationId: string | undefined) {
  const [data, setData]         = useState<StatusHistory[] | null>(null);
  const [isLoading, setLoading] = useState(!!applicationId);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!applicationId) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      setData(await listStatusHistory(applicationId));
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}

// ── Recent activity (for Dashboard) ──────────────────────────────────────────
export function useRecentActivity() {
  const [data, setData]         = useState<StatusHistory[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list  = await listApplications({ limit: 3 });
      const items = (list.items ?? []) as Application[];
      const histories = await Promise.all(
        items.map(app => listStatusHistory(app.id).catch(() => []))
      );
      const all = (histories.flat() as StatusHistory[])
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 4);
      setData(all);
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error };
}

// ── Visa types ────────────────────────────────────────────────────────────────
export function useVisaTypes() {
  const [data, setData]         = useState<VisaType[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listVisaTypes();
      setData(Array.isArray(res) ? res : (res as { items?: VisaType[] }).items ?? []);
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