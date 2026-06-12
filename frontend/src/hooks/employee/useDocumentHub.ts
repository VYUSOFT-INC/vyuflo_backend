// src/hooks/useDocumentHub.ts
import { useState, useEffect, useCallback } from "react";
import documentHubApi from "../../api/employee/documentHub.api";
import type {
  ActivityItem,
  ApplicationTab,
  HubDocument,
  HubRequirements,
  StorageInfo,
} from "../../types/employee/documentHub.types";

export function useDocumentHub() {
  const [documents,       setDocuments]      = useState<HubDocument[]>([]);
  const [requirements,    setRequirements]   = useState<HubRequirements | null>(null);
  const [activity,        setActivity]       = useState<ActivityItem[]>([]);
  const [storage,         setStorage]        = useState<StorageInfo>({ used_mb: 0, total_mb: 50 });
  const [applicationTabs, setApplicationTabs] = useState<ApplicationTab[]>([]);
  const [isLoading,       setIsLoading]      = useState(true);
  const [error,           setError]          = useState<string | null>(null);
  const [uploading,       setUploading]      = useState(false);
  const [uploadError,     setUploadError]    = useState<string | null>(null);

  const [viewMode,    setViewMode]    = useState<"grid" | "list">("grid");
  const [searchQuery, setSearchQuery] = useState("");

  // "all" = show everything, or an application UUID = filter to that app
  const [activeFilter, setActiveFilterState] = useState<string>("all");

  // ── Fetch everything ──────────────────────────────────────────────────────
  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [docs, tabs] = await Promise.all([
        documentHubApi.listDocuments(),
        documentHubApi.getAllApplicationTabs(),
      ]);

      setDocuments(docs);
      setApplicationTabs(tabs);
      setStorage(documentHubApi.getStorageInfo(docs));
      setActivity(documentHubApi.getActivity(docs));

      // Default: load requirements for first in_progress app, else first app
      const firstApp = tabs.find(t => t.status === "in_progress") ?? tabs[0];
      if (firstApp) {
        setActiveFilterState(firstApp.id);
        const reqs = await documentHubApi.getRequirements(firstApp.id).catch(() => null);
        setRequirements(reqs);
      } else {
        setActiveFilterState("all");
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err?.response?.data?.detail ?? "Failed to load documents.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ── Switch active filter + reload requirements for that app ───────────────
  const setActiveFilter = useCallback(async (filterId: string) => {
    setActiveFilterState(filterId);

    if (filterId === "all") {
      setRequirements(null);
      return;
    }

    // filterId is an application UUID — load its task checklist
    try {
      const reqs = await documentHubApi.getRequirements(filterId);
      setRequirements(reqs);
    } catch {
      setRequirements(null);
    }
  }, []);

  // ── Upload ────────────────────────────────────────────────────────────────
  const uploadDocument = useCallback(async (file: File, applicationId?: string) => {
    setUploading(true);
    setUploadError(null);
    try {
      await documentHubApi.uploadDocument(file, applicationId);
      await fetchAll();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setUploadError(err?.response?.data?.detail ?? "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }, [fetchAll]);

  // ── Delete ────────────────────────────────────────────────────────────────
  const deleteDocument = useCallback(async (id: string) => {
    try {
      await documentHubApi.deleteDocument(id);
      setDocuments(prev => prev.filter(d => d.id !== id));
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err?.response?.data?.detail ?? "Delete failed.");
    }
  }, []);

  // ── Filter documents ──────────────────────────────────────────────────────
  const filtered = documents.filter(doc => {
    const matchSearch =
      !searchQuery ||
      doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.document_type.toLowerCase().includes(searchQuery.toLowerCase());

    // "all" shows everything; UUID filters to that application
    const matchFilter =
      activeFilter === "all"
        ? true
        : doc.application_id === activeFilter;

    return matchSearch && matchFilter;
  });

  return {
    documents:       filtered,
    allDocuments:    documents,
    requirements,
    activity,
    storage,
    applicationTabs,          // ← array of { id, label, visa_code, status }
    isLoading,
    error,
    uploading,
    uploadError,
    viewMode,        setViewMode,
    activeFilter,
    setActiveFilter,           // ← async, also reloads requirements
    searchQuery,     setSearchQuery,
    uploadDocument,
    deleteDocument,
    refetch: fetchAll,
  };
}