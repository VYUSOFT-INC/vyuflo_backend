// src/api/notifications.api.ts
import axios from "../axios";
import type {
  Notification,
  NotificationListResponse,
  NotificationStatsResponse,
  NotificationPreferences,
  UpdatePreferencesRequest,
  MarkReadResponse,
  NotificationCategory,
} from "../../types/employee/notification.types";

export const notificationsApi = {

  // ── GET /notifications ─────────────────────────────────────────────────────
  // Returns paginated list for the authenticated user
  list: async (params?: {
    category?:  NotificationCategory;
    is_read?:   boolean;
    priority?:  string;
    limit?:     number;
    offset?:    number;
  }): Promise<NotificationListResponse> => {
    const res = await axios.get<NotificationListResponse>("/notifications", { params });
    return res.data;
  },

  // ── GET /notifications/stats ───────────────────────────────────────────────
  stats: async (): Promise<NotificationStatsResponse> => {
    const res = await axios.get<NotificationStatsResponse>("/notifications/stats");
    return res.data;
  },

  // ── GET /notifications/:id ─────────────────────────────────────────────────
  get: async (id: string): Promise<Notification> => {
    const res = await axios.get<Notification>(`/notifications/${id}`);
    return res.data;
  },

  // ── POST /notifications/:id/read ───────────────────────────────────────────
  markRead: async (id: string): Promise<MarkReadResponse> => {
    const res = await axios.post<MarkReadResponse>(`/notifications/${id}/read`);
    return res.data;
  },

  // ── POST /notifications/read-all ───────────────────────────────────────────
  markAllRead: async (category?: NotificationCategory): Promise<MarkReadResponse> => {
    const res = await axios.post<MarkReadResponse>("/notifications/read-all", {
      ...(category ? { category } : {}),
    });
    return res.data;
  },

  // ── POST /notifications/:id/dismiss ───────────────────────────────────────
  dismiss: async (id: string): Promise<MarkReadResponse> => {
    const res = await axios.post<MarkReadResponse>(`/notifications/${id}/dismiss`);
    return res.data;
  },

  // ── GET /notifications/preferences ────────────────────────────────────────
  getPreferences: async (): Promise<NotificationPreferences> => {
    const res = await axios.get<NotificationPreferences>("/notifications/preferences");
    return res.data;
  },

  // ── PATCH /notifications/preferences ──────────────────────────────────────
  updatePreferences: async (
    body: UpdatePreferencesRequest
  ): Promise<NotificationPreferences> => {
    const res = await axios.patch<NotificationPreferences>(
      "/notifications/preferences",
      body
    );
    return res.data;
  },
};

// ── Named exports matching application.api.ts pattern ─────────────────────────

export const listNotifications  = (p?: Parameters<typeof notificationsApi.list>[0]) =>
  notificationsApi.list(p);

export const getNotificationStats = () =>
  notificationsApi.stats();

export const markNotificationRead = (id: string) =>
  notificationsApi.markRead(id);

export const markAllNotificationsRead = (cat?: NotificationCategory) =>
  notificationsApi.markAllRead(cat);

export const dismissNotification = (id: string) =>
  notificationsApi.dismiss(id);

export const getNotificationPreferences = () =>
  notificationsApi.getPreferences();

export const updateNotificationPreferences = (body: UpdatePreferencesRequest) =>
  notificationsApi.updatePreferences(body);