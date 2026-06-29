// src/types/notification.types.ts
import type { AxiosError } from "axios";

export type NotificationType =
  | "missing_document" | "deadline_approaching" | "policy_update"
  | "document_approved" | "case_status_updated" | "participant_added"
  | "document_comment" | "weekly_summary" | "security_alert"
  | "payment_receipt" | "immigration_news";

// Exact DB enum values from notification_category_enum
export type NotificationCategory =
  | "case_update" | "deadline" | "news" | "security" | "billing";

export type TabFilter = "all" | NotificationCategory;

export type NotificationPriority = "urgent" | "high" | "medium" | "low";

export interface Notification {
  id: string; user_id: string;
  notification_type: NotificationType;
  category: NotificationCategory;
  priority: NotificationPriority;
  title: string; body: string;
  application_id?: string | null; document_id?: string | null;
  case_reference?: string | null; actor_id?: string | null; actor_label?: string | null;
  cta_primary_label?: string | null; cta_primary_url?: string | null;
  cta_secondary_label?: string | null; cta_secondary_url?: string | null;
  is_read: boolean; read_at?: string | null;
  is_dismissed: boolean; dismissed_at?: string | null;
  sent_via_email: boolean; sent_via_push: boolean; sent_via_sms: boolean;
  expires_at?: string | null; created_at: string; updated_at: string;
}

export interface NotificationPreferences {
  id: string; user_id: string;
  email_enabled: boolean; push_enabled: boolean; sms_enabled: boolean;
  notify_case_updates: boolean; notify_deadlines: boolean;
  notify_document_updates: boolean; notify_news: boolean;
  notify_security_alerts: boolean; notify_billing: boolean;
  notify_weekly_summary: boolean; updated_at: string;
}

export interface NotificationListResponse {
  items: Notification[]; total: number;
  unread_count: number; urgent_count: number; has_more: boolean;
}
export interface NotificationStatsResponse {
  urgent_count: number; unread_count: number; week_count: number; news_count: number;
}
export interface MarkReadResponse { updated: number; message: string; }
export interface UpdatePreferencesRequest {
  email_enabled?: boolean; push_enabled?: boolean; sms_enabled?: boolean;
  notify_case_updates?: boolean; notify_deadlines?: boolean;
  notify_document_updates?: boolean; notify_news?: boolean;
  notify_security_alerts?: boolean; notify_billing?: boolean;
  notify_weekly_summary?: boolean;
}
export interface UseNotificationsReturn {
  notifications: Notification[]; total: number; unreadCount: number;
  urgentCount: number; hasMore: boolean; loading: boolean; error: string | null;
  refetch: () => void; loadMore: () => void;
}
export interface UseNotificationStatsReturn {
  stats: NotificationStatsResponse | null; loading: boolean; error: string | null; refetch: () => void;
}
export interface UseNotificationPreferencesReturn {
  prefs: NotificationPreferences | null; loading: boolean; saving: boolean;
  error: string | null; update: (data: UpdatePreferencesRequest) => Promise<void>;
}
export function extractMessage(e: unknown): string {
  const err = e as AxiosError<{ detail: string }>;
  return err.response?.data?.detail ?? (e instanceof Error ? e.message : "Something went wrong.");
}