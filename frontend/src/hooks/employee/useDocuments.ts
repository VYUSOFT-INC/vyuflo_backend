// src/hooks/useDocuments.ts
import { useState, useEffect, useCallback } from "react";
import type { AxiosError } from "axios";
import documentsApi from "../../api/employee/documents.api";
import type { Document, DocumentListResponse } from "../../types/employee/document.types";

// Re-export types so existing imports from this file still work
export type { Document, DocumentListResponse };
export type { DocumentStatus } from "../../types/employee/document.types";

// ── Error helper ──────────────────────────────────────────────────────────────
function extractMessage(e: unknown): string {
  const err = e as AxiosError<{ detail: string }>;
  return (
    err.response?.data?.detail ??
    (e instanceof Error ? e.message : "Something went wrong.")
  );
}

// ── useDocuments — list docs for current user, optionally filtered by app ─────
export function useDocuments(applicationId?: string) {
  const [data, setData]         = useState<Document[]>([]);
  // isLoading starts true only when we have something to fetch
  const [isLoading, setLoading] = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = applicationId
        ? await documentsApi.listByApplication(applicationId)
        : await documentsApi.list();
      setData(Array.isArray(res) ? res : (res as DocumentListResponse).items ?? []);
    } catch (e) {
      setError(extractMessage(e));
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}

// ── useDocument — single document by ID ──────────────────────────────────────
export function useDocument(documentId: string | undefined) {
  const [data, setData]         = useState<Document | null>(null);
  const [isLoading, setLoading] = useState(!!documentId);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!documentId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setData(await documentsApi.get(documentId));
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}