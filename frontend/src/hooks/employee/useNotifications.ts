// src/hooks/useNotifications.ts
import { useState, useEffect, useCallback } from "react";
// import type { AxiosError } from "axios";
import type {
  Notification,
  NotificationCategory,
  NotificationPreferences,
  NotificationStatsResponse,
  UpdatePreferencesRequest,
  UseNotificationsReturn,
  UseNotificationStatsReturn,
  UseNotificationPreferencesReturn,
} from "../../types/employee/notification.types";
import { extractMessage } from "../../types/employee/notification.types";
import {
  listNotifications,
  getNotificationStats,
  markNotificationRead,
  markAllNotificationsRead,
  dismissNotification,
  getNotificationPreferences,
  updateNotificationPreferences,
} from "../../api/employee/notifications.api";

const PAGE_SIZE = 20;

// ── useNotifications — paginated list + filter ────────────────────────────────

export function useNotifications(params?: {
  category?: NotificationCategory;
  is_read?:  boolean;
}): UseNotificationsReturn & {
  markRead:    (id: string) => Promise<void>;
  markAllRead: (cat?: NotificationCategory) => Promise<void>;
  dismiss:     (id: string) => Promise<void>;
} {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [total,         setTotal]         = useState(0);
  const [unreadCount,   setUnreadCount]   = useState(0);
  const [urgentCount,   setUrgentCount]   = useState(0);
  const [hasMore,       setHasMore]       = useState(false);
  const [offset,        setOffset]        = useState(0);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState<string | null>(null);

  const paramsKey = JSON.stringify(params);

  const load = useCallback(async (reset = true) => {
    setLoading(true);
    setError(null);
    try {
      const currentOffset = reset ? 0 : offset;
      const data = await listNotifications({
        ...params,
        limit:  PAGE_SIZE,
        offset: currentOffset,
      });
      setNotifications(prev =>
        reset ? data.items : [...prev, ...data.items]
      );
      setTotal(data.total);
      setUnreadCount(data.unread_count);
      setUrgentCount(data.urgent_count);
      setHasMore(data.has_more);
      if (reset) setOffset(PAGE_SIZE);
      else setOffset(currentOffset + PAGE_SIZE);
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey, offset]);

  const refetch  = useCallback(() => load(true),  [load]);
  const loadMore = useCallback(() => load(false), [load]);

  useEffect(() => { void load(true); }, [paramsKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Mark single read — optimistic update
  const markRead = useCallback(async (id: string) => {
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, is_read: true } : n)
    );
    setUnreadCount(prev => Math.max(0, prev - 1));
    try {
      await markNotificationRead(id);
    } catch {
      // revert on failure
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, is_read: false } : n)
      );
      setUnreadCount(prev => prev + 1);
    }
  }, []);

  // Mark all read — optimistic
  const markAllRead = useCallback(async (cat?: NotificationCategory) => {
    setNotifications(prev =>
      prev.map(n =>
        (!cat || n.category === cat) ? { ...n, is_read: true } : n
      )
    );
    setUnreadCount(0);
    try {
      await markAllNotificationsRead(cat);
    } catch {
      void load(true);
    }
  }, [load]);

  // Dismiss — remove from list optimistically
  const dismiss = useCallback(async (id: string) => {
    const target = notifications.find(n => n.id === id);
    setNotifications(prev => prev.filter(n => n.id !== id));
    if (target && !target.is_read) setUnreadCount(prev => Math.max(0, prev - 1));
    try {
      await dismissNotification(id);
    } catch {
      if (target) setNotifications(prev => [target, ...prev]);
    }
  }, [notifications]);

  return {
    notifications, total, unreadCount, urgentCount, hasMore,
    loading, error, refetch, loadMore,
    markRead, markAllRead, dismiss,
  };
}

// ── useNotificationStats — header badge counts ────────────────────────────────

export function useNotificationStats(): UseNotificationStatsReturn {
  const [stats,   setStats]   = useState<NotificationStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStats(await getNotificationStats());
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { stats, loading, error, refetch: load };
}

// ── useNotificationPreferences ────────────────────────────────────────────────

export function useNotificationPreferences(): UseNotificationPreferencesReturn {
  const [prefs,   setPrefs]   = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving,  setSaving]  = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setPrefs(await getNotificationPreferences());
      } catch (e) {
        setError(extractMessage(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const update = useCallback(async (data: UpdatePreferencesRequest) => {
    setSaving(true);
    setError(null);
    // Optimistic update
    setPrefs(prev => prev ? { ...prev, ...data } : prev);
    try {
      const updated = await updateNotificationPreferences(data);
      setPrefs(updated);
    } catch (e) {
      setError(extractMessage(e));
      // Revert optimistic — refetch
      try { setPrefs(await getNotificationPreferences()); } catch { /* noop */ }
    } finally {
      setSaving(false);
    }
  }, []);

  return { prefs, loading, saving, error, update };
}