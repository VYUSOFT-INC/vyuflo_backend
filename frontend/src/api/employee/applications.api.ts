// src/api/applications.api.ts
import type { VisaType } from "../../types/employee/application.types";
import axios from "../axios";

export const applicationsApi = {

  // GET /applications — list with KPI summary
  list: async (params?: {
    status?:       string;
    visa_type_id?: string;
    limit?:        number;
    offset?:       number;
  }) => {
    const res = await axios.get("/applications", { params });
    return res.data;
  },

  // GET /applications/:id — single application
  get: async (id: string) => {
    const res = await axios.get(`/applications/${id}`);
    return res.data;
  },

  // POST /applications — create new
  create: async (body: {
    visa_type_id:      string;
    sponsor_employer?: string;
    notes?:            string;
  }) => {
    const res = await axios.post("/applications", body);
    return res.data;
  },

  // PATCH /applications/:id — update
  update: async (id: string, body: Record<string, unknown>) => {
    const res = await axios.patch(`/applications/${id}`, body);
    return res.data;
  },

  // PATCH /applications/:id/status — change status
  updateStatus: async (id: string, body: {
    status:         string;
    current_stage?: string;
    note?:          string;
  }) => {
    const res = await axios.patch(`/applications/${id}/status`, body);
    return res.data;
  },

  // DELETE /applications/:id
  delete: async (id: string) => {
    const res = await axios.delete(`/applications/${id}`);
    return res.data;
  },

  // GET /applications/:id/status-history
  getStatusHistory: async (id: string) => {
    const res = await axios.get(`/applications/${id}/status-history`);
    return res.data;
  },

  // GET /applications/:id/tasks
  getTasks: async (id: string) => {
    const res = await axios.get(`/applications/${id}/tasks`);
    return res.data;
  },

  // POST /applications/:id/tasks — create task
  createTask: async (appId: string, body: {
    task_name:    string;
    description?: string;
    is_required?: boolean;
    sort_order?:  number;
  }) => {
    const res = await axios.post(`/applications/${appId}/tasks`, body);
    return res.data;
  },

  // PATCH /applications/:id/tasks/:taskId/complete
  // FIX — now sends document_id so backend can link the uploaded doc to the task
  completeTask: async (
    appId:       string,
    taskId:      string,
    is_completed: boolean,
    document_id?: string,      // ← ADD — links uploaded document to task
  ) => {
    const res = await axios.patch(
      `/applications/${appId}/tasks/${taskId}/complete`,
      {
        is_completed,
        ...(document_id ? { document_id } : {}),   // only send if present
      }
    );
    return res.data;
  },

  // GET /visa-types/:id — single visa type
  getVisaType: async (id: string) => {
    const res = await axios.get(`/visa-types/${id}`);
    return res.data;
  },

  // POST /documents/upload — multipart upload
  uploadDocument: async (formData: FormData) => {
    const res = await axios.post("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  },
};

// ── Named exports ──────────────────────────────────────────────────────────────
export const listApplications  = (params?: Parameters<typeof applicationsApi.list>[0]) =>
  applicationsApi.list(params);

export const getApplication    = (id: string) =>
  applicationsApi.get(id);

export const listTasks         = (applicationId: string) =>
  applicationsApi.getTasks(applicationId);

export const listStatusHistory = (applicationId: string) =>
  applicationsApi.getStatusHistory(applicationId);

export async function createApplication(body: {
  visa_type_id:      string;
  sponsor_employer?: string;
  notes?:            string;
}) {
  const res = await axios.post("/applications", body);
  return res.data;
}

// FIX — now passes document_id through to API
export const completeTask = (
  appId:       string,
  taskId:      string,
  is_completed: boolean,
  document_id?: string,        // ← ADD
) => applicationsApi.completeTask(appId, taskId, is_completed, document_id);

export const createTask = (
  appId: string,
  body:  Parameters<typeof applicationsApi.createTask>[1],
) => applicationsApi.createTask(appId, body);

export const getVisaType     = (id: string)    => applicationsApi.getVisaType(id);
export const uploadDocument  = (fd: FormData)  => applicationsApi.uploadDocument(fd);

export async function listVisaTypes(): Promise<VisaType[]> {
  const res = await axios.get("/visa-types");
  return res.data;
}