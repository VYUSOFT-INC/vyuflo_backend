// src/api/documentHub.api.ts
import documentsApi from "../employee/documents.api";
import axios from "../axios";

import type { Document } from "../../types/employee/document.types";

import type {
  HubDocument,
  HubRequirements,
  ActivityItem,
  StorageInfo,
  RequirementItem,
  ApplicationTab,
} from "../../types/employee/documentHub.types";

// ── Normalise Document → HubDocument ─────────────────────────────────────────

function toFileType(doc: Document): "pdf" | "docx" | "img" | "other" {
  const f = (doc.file_type ?? "").toLowerCase();

  if (f === "pdf") return "pdf";

  if (f === "docx" || f === "doc") return "docx";

  if (["jpg", "jpeg", "png", "gif", "webp"].includes(f)) {
    return "img";
  }

  return "other";
}

function normalise(d: Document): HubDocument {
  return {
    id: d.id,
    name: d.name,

    file_type: toFileType(d),

    status: d.status as HubDocument["status"],

    document_type: d.document_type ?? "Document",

    category: d.category ?? "other",

    application_name: undefined,

    application_id: d.application_id ?? undefined,

    file_size_bytes: d.file_size_bytes ?? 0,

    uploaded_at: d.uploaded_at ?? new Date().toISOString(),

    verified_at: d.verified_at ?? undefined,
  };
}

// =============================================================================

const documentHubApi = {
  // ── Documents ─────────────────────────────────────────────────────────────

  listDocuments: async (): Promise<HubDocument[]> => {
    const docs = await documentsApi.list();

    return docs.map(normalise);
  },

  listByApplication: async (
    applicationId: string
  ): Promise<HubDocument[]> => {
    const docs = await documentsApi.listByApplication(applicationId);

    return docs.map(normalise);
  },

  // ── Applications tabs ────────────────────────────────────────────────────

  getAllApplicationTabs: async (): Promise<ApplicationTab[]> => {
    const res = await axios.get("/applications");

    const apps = (res.data?.items ?? res.data ?? []) as Record<
      string,
      unknown
    >[];

    return apps.map((app) => ({
      id: app.id as string,

      label:
        ((app.visa_type as Record<string, unknown> | undefined)?.code as
          | string
          | undefined) ?? "Application",

      visa_code:
        ((app.visa_type as Record<string, unknown> | undefined)?.code as
          | string
          | undefined) ?? "H-1B",

      status: (app.status as string) ?? "in_progress",
    }));
  },

  // ── Upload ────────────────────────────────────────────────────────────────

  uploadDocument: async (
    file: File,
    applicationId?: string,
    documentType?: string,
    category?: string
  ): Promise<HubDocument> => {
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";

    const autoCategory = ["jpg", "jpeg", "png", "gif", "webp"].includes(ext)
      ? "identity"
      : ext === "pdf"
      ? "legal"
      : "other";

    const doc = await documentsApi.upload({
      application_id: applicationId ?? "",

      document_type:
        documentType ?? file.name.replace(/\.[^/.]+$/, ""),

      category: category ?? autoCategory,

      file,
    });

    return normalise(doc);
  },

  // ── Delete ────────────────────────────────────────────────────────────────

  deleteDocument: async (id: string): Promise<void> => {
    await documentsApi.delete(id);
  },

  // ── File viewer ───────────────────────────────────────────────────────────

  getFileBlob: async (id: string) => {
    return documentsApi.getFile(id);
  },

  // ── Requirements ──────────────────────────────────────────────────────────

  getRequirements: async (
    applicationId?: string
  ): Promise<HubRequirements | null> => {
    try {
      // 1. Applications
      const appsRes = await axios.get("/applications");

      const allApps = (appsRes.data?.items ??
        appsRes.data ??
        []) as Record<string, unknown>[];

      if (!allApps.length) return null;

      // 2. Pick app
      let app: Record<string, unknown>;

      if (applicationId) {
        app =
          allApps.find((a) => a.id === applicationId) ?? allApps[0];
      } else {
        app =
          allApps.find((a) => a.status === "in_progress") ??
          allApps[0];
      }

      const appId = app.id as string;

      // 3. Tasks
      const tasksRes = await axios.get(
        `/applications/${appId}/tasks`
      );

      const tasks = (
        Array.isArray(tasksRes.data)
          ? tasksRes.data
          : tasksRes.data?.items ?? []
      ) as Record<string, unknown>[];

      const done = tasks.filter(
        (t) => t.is_completed === true
      ).length;

      const items: RequirementItem[] = tasks.map((t) => ({
        id: t.id as string,

        task_name:
          ((t.name ?? t.task_name) as string) ?? "Document",

        status: (
          t.is_completed
            ? t.document_id
              ? "verified"
              : "uploaded"
            : t.is_required ?? true
            ? "missing"
            : "required"
        ) as RequirementItem["status"],

        document_id: t.document_id as string | undefined,
      }));

      const visaType = app.visa_type as
        | Record<string, unknown>
        | undefined;

      return {
        application_id: appId,

        visa_code: (visaType?.code as string) ?? "H-1B",

        done,

        total: tasks.length,

        items,
      };
    } catch (e) {
      console.warn("[documentHub] getRequirements failed:", e);

      return null;
    }
  },

  // ── Storage ───────────────────────────────────────────────────────────────

  getStorageInfo: (
    documents: HubDocument[],
    totalMb = 50
  ): StorageInfo => {
    const usedBytes = documents.reduce(
      (sum, d) => sum + (d.file_size_bytes ?? 0),
      0
    );

    return {
      used_mb: usedBytes / (1024 * 1024),

      total_mb: totalMb,
    };
  },

  // ── Activity ──────────────────────────────────────────────────────────────

  getActivity: (
    documents: HubDocument[]
  ): ActivityItem[] => {
    return [...documents]
      .sort(
        (a, b) =>
          new Date(b.uploaded_at).getTime() -
          new Date(a.uploaded_at).getTime()
      )

      .slice(0, 5)

      .map((d) => ({
        id: d.id,

        text: `${d.name} ${
          d.status === "verified"
            ? "verified"
            : "uploaded"
        }`,

        by: "You",

        timestamp: d.uploaded_at,
      }));
  },
};

export default documentHubApi;