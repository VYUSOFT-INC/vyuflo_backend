// src/types/notificationTemplates.types.ts

export interface NotificationTemplate {
  id:                    string;
  event_key:            string;          // trigger event e.g. "Status_Changed_Approved"
  name:                 string;
  description:          string | null;
  channel:              string;          // "email" | "in_app" | "sms" | "push" (backend casing)
  subject:              string | null;
  body_html:            string | null;
  body_text:            string | null;
  available_placeholders: string | null;
  category:             string | null;
  is_active:            boolean;
  updated_at:           string;
  last_modified_by_name: string | null;
  created_at:           string;
}

export interface NotificationTemplateListResponse {
  items:       NotificationTemplate[];
  total:       number;
  page:        number;
  limit:       number;
  total_pages: number;
}

export interface ToggleTemplatePayload {
  is_active: boolean;
}

export interface CreateTemplatePayload {
  event_key:              string;
  name:                   string;
  description?:           string;
  channel:                string;          // "email" | "in_app" | "sms" | "push"
  subject?:               string;
  body_html?:             string;
  body_text?:             string;
  available_placeholders?: string;
  category?:              string;
  is_active:              boolean;
}