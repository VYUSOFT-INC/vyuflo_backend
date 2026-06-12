// src/api/notifications.api.ts

import axios from "./axios";

// ── Types ──────────────────────────────────────────────────────────
export type ChannelType = "Email" | "In-App" | "SMS" | "Push";

export interface NotificationTemplate {
  id:           string;
  name:         string;
  description:  string;
  channel:      ChannelType;
  trigger:      string;
  status:       "active" | "inactive";
  subject?:     string;
  body?:        string;
  variables?:   string[];
  lastModified: string;
  modifiedBy:   string;
  iconBg:       string;
}

export interface TemplateListResponse {
  templates:  NotificationTemplate[];
  total:      number;
  page:       number;
  limit:      number;
  totalPages: number;
}

export interface TriggerOption {
  key:   string;
  label: string;
}

export interface ChannelOption {
  key:     ChannelType;
  label:   string;
  iconBg:  string;
  color:   string;
}

export interface CreateTemplatePayload {
  name:     string;
  channel:  ChannelType;
  trigger:  string;
  subject?: string;
  body:     string;
  status:   "active" | "inactive";
}

// ── API calls ──────────────────────────────────────────────────────

/** GET /admin/notification-templates */
export const fetchTemplates = async (params?: {
  search?:  string;
  channel?: ChannelType;
  status?:  "active" | "inactive";
  trigger?: string;
  page?:    number;
  limit?:   number;
}): Promise<TemplateListResponse> => {
  const res = await axios.get("/admin/notification-templates", { params });
  return res.data.data;
};

/** GET /admin/notification-templates/:id */
export const fetchTemplateById = async (id: string): Promise<NotificationTemplate> => {
  const res = await axios.get(`/admin/notification-templates/${id}`);
  return res.data.data.template;
};

/** POST /admin/notification-templates */
export const createTemplate = async (payload: CreateTemplatePayload): Promise<NotificationTemplate> => {
  const res = await axios.post("/admin/notification-templates", payload);
  return res.data.data.template;
};

/** PUT /admin/notification-templates/:id */
export const updateTemplate = async (
  id: string,
  payload: Partial<CreateTemplatePayload>
): Promise<NotificationTemplate> => {
  const res = await axios.put(`/admin/notification-templates/${id}`, payload);
  return res.data.data.template;
};

/** DELETE /admin/notification-templates/:id */
export const deleteTemplate = async (id: string): Promise<void> => {
  await axios.delete(`/admin/notification-templates/${id}`);
};

/** PUT /admin/notification-templates/:id/status */
export const toggleTemplateStatus = async (
  id: string,
  status: "active" | "inactive"
): Promise<NotificationTemplate> => {
  const res = await axios.put(`/admin/notification-templates/${id}/status`, { status });
  return res.data.data.template;
};

/** POST /admin/notification-templates/:id/duplicate */
export const duplicateTemplate = async (id: string, newName: string): Promise<NotificationTemplate> => {
  const res = await axios.post(`/admin/notification-templates/${id}/duplicate`, { newName });
  return res.data.data.template;
};

/** POST /admin/notification-templates/:id/test */
export const sendTestNotification = async (
  id: string,
  recipientEmail: string,
  sampleData: Record<string, string>
): Promise<{ message: string }> => {
  const res = await axios.post(`/admin/notification-templates/${id}/test`, {
    recipientEmail,
    sampleData,
  });
  return res.data.data;
};

/** GET /admin/notification-templates/triggers */
export const fetchTriggerOptions = async (): Promise<TriggerOption[]> => {
  const res = await axios.get("/admin/notification-templates/triggers");
  return res.data.data.triggers;
};

/** GET /admin/notification-templates/channels */
export const fetchChannelOptions = async (): Promise<ChannelOption[]> => {
  const res = await axios.get("/admin/notification-templates/channels");
  return res.data.data.channels;
};
