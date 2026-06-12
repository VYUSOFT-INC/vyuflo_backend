// src/api/notificationTemplates.api.ts
import axios from "../axios";
import type {
  NotificationTemplateListResponse,
  NotificationTemplate,
  ToggleTemplatePayload,
  CreateTemplatePayload,
} from "../../types/admin/notificationTemplates.types";

// NOTE: paths have NO "/v1" prefix because the axios baseURL already ends
// with /api/v1 (same as auth.api.ts which uses "/auth/me").

/** GET /notification-templates — list (paginated) */
export const fetchTemplates = async (
  params?: { page?: number; limit?: number }
): Promise<NotificationTemplateListResponse> => {
  const res = await axios.get("/notification-templates", { params });
  return res.data;
};

/** PATCH /notification-templates/{id}/toggle — turn status on/off */
export const toggleTemplate = async (
  templateId: string,
  payload: ToggleTemplatePayload
): Promise<NotificationTemplate> => {
  const res = await axios.patch(
    `/notification-templates/${templateId}/toggle`,
    payload
  );
  return res.data;
};

/** DELETE /notification-templates/{id} — delete a template */
export const deleteTemplate = async (templateId: string): Promise<void> => {
  await axios.delete(`/notification-templates/${templateId}`);
};

/** POST /notification-templates — create a new template */
export const createTemplate = async (
  payload: CreateTemplatePayload
): Promise<NotificationTemplate> => {
  const res = await axios.post("/notification-templates", payload);
  return res.data;
};