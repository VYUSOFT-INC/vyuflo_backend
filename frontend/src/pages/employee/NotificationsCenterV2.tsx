// src/pages/employee/NotificationsCenterV2.tsx
import { useState, useMemo } from "react";
import { useNotifications, useNotificationStats, useNotificationPreferences } from "../../hooks/employee/useNotifications";
import type { Notification, NotificationCategory, TabFilter } from "../../types/employee/notification.types";
import { PageHeader, PageContent } from "../../components/layout/Pageheader";

// ─── Inline SVG icons ─────────────────────────────────────────────────────────
const IconAlert      = () => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>);
const IconClock      = () => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>);
const IconFile       = () => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>);
const IconNews       = () => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a4 4 0 01-8 0V6"/><path d="M18 14H10M18 10H10M18 18H10"/></svg>);
const IconShield     = () => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>);
const IconCreditCard = () => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>);
const IconBriefcase  = () => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/></svg>);
const IconSettings   = () => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>);
const IconFilter     = () => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>);
const IconChevronDown = () => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>);
const IconCheck      = () => (<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>);
const IconBell       = () => (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>);
const IconCalendar   = () => (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>);
const IconNewspaper  = () => (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a4 4 0 01-8 0V6"/><path d="M18 14h-8M18 10h-8M18 18h-8"/></svg>);
const IconTrendingUp = () => (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>);
const IconMoreVertical = () => (<svg width="4" height="16" viewBox="0 0 4 20" fill="currentColor"><circle cx="2" cy="2" r="2"/><circle cx="2" cy="10" r="2"/><circle cx="2" cy="18" r="2"/></svg>);
const IconDot = () => (<div className="w-[8px] h-[8px] rounded-full bg-[#4F46E5] flex-shrink-0 mt-[6px]" />);

// ─── Category styles ──────────────────────────────────────────────────────────
const CATEGORY_STYLES: Record<string, { bg: string; icon: string }> = {
  document:    { bg: "bg-[#EFF6FF]", icon: "text-[#3B82F6]" },
  deadline:    { bg: "bg-[#FFF7ED]", icon: "text-[#F97316]" },
  case_update: { bg: "bg-[#F0FDF4]", icon: "text-[#22C55E]" },
  news:        { bg: "bg-[#F5F3FF]", icon: "text-[#8B5CF6]" },
  security:    { bg: "bg-[#FEF2F2]", icon: "text-[#EF4444]" },
  billing:     { bg: "bg-[#ECFDF5]", icon: "text-[#10B981]" },
};
function getCategoryIcon(cat: string) {
  switch (cat) {
    case "document":    return <IconFile />;
    case "deadline":    return <IconClock />;
    case "case_update": return <IconBriefcase />;
    case "news":        return <IconNews />;
    case "security":    return <IconShield />;
    case "billing":     return <IconCreditCard />;
    default:            return <IconAlert />;
  }
}

// ─── Stat card ────────────────────────────────────────────────────────────────
function StatCard({ value, label, badge, badgeCls, iconBg, iconColor, icon, loading }: {
  value: number; label: string; badge: string; badgeCls: string;
  iconBg: string; iconColor: string; icon: React.ReactNode; loading?: boolean;
}) {
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-[16px] sm:p-[20px] lg:p-[24px]
                    flex flex-col gap-[8px] flex-1 min-w-0">
      <div className="flex items-center justify-between">
        <div className={`w-[40px] h-[40px] sm:w-[48px] sm:h-[48px] rounded-[10px] ${iconBg} ${iconColor}
                         flex items-center justify-center flex-shrink-0`}>
          {icon}
        </div>
        <span className={`text-[10px] sm:text-[11px] font-semibold px-[8px] sm:px-[10px] py-[3px]
                          rounded-full ${badgeCls}`}>
          {badge}
        </span>
      </div>
      <p className="text-[24px] sm:text-[28px] lg:text-[32px] font-bold text-[#111827] leading-none mt-[6px] sm:mt-[8px]">
        {loading ? <span className="text-[18px] text-[#9CA3AF]">…</span> : value}
      </p>
      <p className="text-[11px] sm:text-[13px] text-[#6B7280] leading-tight">{label}</p>
    </div>
  );
}

// ─── Toggle ───────────────────────────────────────────────────────────────────
function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button onClick={onChange}
      className={`relative w-[44px] h-[24px] rounded-full transition-colors flex-shrink-0 ${checked ? "bg-[#4F46E5]" : "bg-[#E5E7EB]"}`}>
      <div className={`absolute top-[2px] w-[20px] h-[20px] bg-white rounded-full shadow-sm transition-transform ${checked ? "translate-x-[22px]" : "translate-x-[2px]"}`} />
    </button>
  );
}

// ─── Notification row ─────────────────────────────────────────────────────────
function NotificationRow({ notif, onMarkRead, onDismiss }: {
  notif: Notification; onMarkRead: (id: string) => void; onDismiss: (id: string) => void;
}) {
  const styles = CATEGORY_STYLES[notif.category] ?? { bg: "bg-[#F9FAFB]", icon: "text-[#6B7280]" };
  return (
    <div className={`border-b border-[#F3F4F6] last:border-0 ${!notif.is_read ? "bg-[#FAFAFA]" : "bg-white"}`}>
      <div className="px-[16px] sm:px-[24px] lg:px-[28px] py-[16px] sm:py-[20px] lg:py-[24px]">
        <div className="flex items-start gap-[12px] sm:gap-[16px]">
          <div className={`w-[38px] h-[38px] sm:w-[44px] sm:h-[44px] rounded-[10px] ${styles.bg} ${styles.icon}
                           flex items-center justify-center flex-shrink-0 mt-[2px]`}>
            {getCategoryIcon(notif.category)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start gap-[6px] sm:gap-[8px] flex-wrap">
              <h3 className="text-[13px] sm:text-[14px] lg:text-[15px] font-semibold text-[#111827]
                             leading-[20px] sm:leading-[22px] flex-1 min-w-0">
                {notif.title}
              </h3>
              {notif.priority === "urgent" && (
                <span className="text-[10px] font-bold px-[6px] sm:px-[8px] py-[3px] rounded-full bg-[#FEF2F2] text-[#DC2626] flex-shrink-0">
                  URGENT
                </span>
              )}
              {notif.priority === "high" && (
                <span className="text-[10px] font-bold px-[6px] sm:px-[8px] py-[3px] rounded-full bg-[#FFF7ED] text-[#C2410C] flex-shrink-0">
                  HIGH
                </span>
              )}
              {!notif.is_read && (
                <div className="w-[8px] h-[8px] rounded-full bg-[#4F46E5] flex-shrink-0 mt-[6px]" />
              )}
            </div>
            <p className="text-[12px] sm:text-[13px] text-[#6B7280] mt-[4px] sm:mt-[6px] leading-[18px] sm:leading-[20px]">
              {notif.body}
            </p>
            <div className="flex items-center flex-wrap gap-[8px] sm:gap-[12px] mt-[8px] sm:mt-[10px]">
              {notif.case_reference && (
                <span className="text-[11px] text-[#4F46E5] font-medium">{notif.case_reference}</span>
              )}
              {notif.actor_label && (
                <span className="text-[11px] text-[#4F46E5] font-medium">{notif.actor_label}</span>
              )}
              <span className="text-[11px] text-[#9CA3AF]">
                {new Date(notif.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              </span>
            </div>
          </div>
          <button onClick={() => onDismiss(notif.id)}
            className="text-[#D1D5DB] hover:text-[#6B7280] transition-colors flex-shrink-0 mt-[2px] p-[4px]">
            <IconMoreVertical />
          </button>
        </div>
        {(notif.cta_primary_label || notif.cta_secondary_label) && (
          <div className="flex items-center flex-wrap gap-[8px] sm:gap-[10px] mt-[12px] sm:mt-[16px] ml-[50px] sm:ml-[60px]">
            {notif.cta_primary_label && (
              <button onClick={() => onMarkRead(notif.id)}
                className="text-[12px] sm:text-[13px] font-medium px-[14px] sm:px-[16px] py-[6px] sm:py-[7px]
                           rounded-[8px] bg-[#4F46E5] text-white hover:bg-[#4338CA] transition-colors">
                {notif.cta_primary_label}
              </button>
            )}
            {notif.cta_secondary_label && (
              <button onClick={() => onMarkRead(notif.id)}
                className="text-[12px] sm:text-[13px] font-medium px-[14px] sm:px-[16px] py-[6px] sm:py-[7px]
                           rounded-[8px] border border-[#E5E7EB] text-[#374151] hover:bg-[#F9FAFB] transition-colors">
                {notif.cta_secondary_label}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────
const TABS: { id: TabFilter; label: string }[] = [
  { id: "all",         label: "All"          },
  { id: "case_update", label: "Case Updates" },
  { id: "deadline",    label: "Deadlines"    },
  { id: "news",        label: "News"         },
];

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function NotificationsCenterV2() {
  const [activeTab, setActiveTab] = useState<TabFilter>("all");

  const {
    notifications, unreadCount, urgentCount, loading, error,
    markRead, markAllRead, dismiss, loadMore, hasMore,
  } = useNotifications({
    category: activeTab === "all" ? undefined : activeTab as NotificationCategory,
  });

  const { stats, loading: statsLoading } = useNotificationStats();
  const { prefs, saving, update: updatePrefs } = useNotificationPreferences();

  const deadlines  = useMemo(() => notifications.filter(n => n.category === "deadline").slice(0, 3), [notifications]);
  const newsItems  = useMemo(() => notifications.filter(n => n.category === "news").slice(0, 3), [notifications]);
  const caseNotifs = notifications.filter(n => n.category === "case_update");

  return (
    <div className="flex flex-col h-full">

      {/* ── PageHeader — sticky, handles mobile logo ── */}
      <PageHeader
        title="Notifications Center"
        subtitle="Stay updated with your cases, deadlines, and immigration news"
        showSearch={false}
        actions={
          <button onClick={() => markAllRead()}
            className="flex items-center gap-[6px] text-[12px] sm:text-[13px] font-medium
                       text-[#4F46E5] hover:text-[#4338CA] transition-colors whitespace-nowrap">
            <IconCheck />
            <span className="hidden sm:inline">Mark All as Read</span>
            <span className="sm:hidden">Mark All</span>
          </button>
        }
      />

      {/* ── PageContent — scrollable ── */}
      <PageContent>
        <div className="flex flex-col gap-[20px] sm:gap-[24px] lg:gap-[28px]">

          {/* ── Stat cards — 2-col mobile, 4-col xl ── */}
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-[12px] sm:gap-[16px]">
            <StatCard loading={statsLoading}
              value={stats?.urgent_count ?? urgentCount} label="Urgent Actions Required"
              badge="Urgent" badgeCls="bg-[#FEF2F2] text-[#DC2626]"
              iconBg="bg-[#FEF2F2]" iconColor="text-[#DC2626]" icon={<IconAlert />} />
            <StatCard loading={statsLoading}
              value={stats?.unread_count ?? unreadCount} label="Unread Notifications"
              badge="New" badgeCls="bg-[#EFF6FF] text-[#2563EB]"
              iconBg="bg-[#EFF6FF]" iconColor="text-[#2563EB]" icon={<IconBell />} />
            <StatCard loading={statsLoading}
              value={stats?.week_count ?? 0} label="Updates This Week"
              badge="Week" badgeCls="bg-[#F0FDF4] text-[#16A34A]"
              iconBg="bg-[#F0FDF4]" iconColor="text-[#16A34A]" icon={<IconTrendingUp />} />
            <StatCard loading={statsLoading}
              value={stats?.news_count ?? 0} label="Immigration News"
              badge="News" badgeCls="bg-[#F5F3FF] text-[#7C3AED]"
              iconBg="bg-[#F5F3FF]" iconColor="text-[#7C3AED]" icon={<IconNewspaper />} />
          </div>

          {/* ── Main 2-col: notification list + right sidebar ── */}
          <div className="flex flex-col xl:flex-row gap-[20px] sm:gap-[24px] items-start">

            {/* ── Notification list ── */}
            <div className="flex-1 min-w-0 w-full">
              <div className="bg-white border border-[#E5E7EB] rounded-[12px] overflow-hidden">

                {/* Toolbar */}
                <div className="px-[14px] sm:px-[16px] pt-[14px] sm:pt-[16px] pb-0 border-b border-[#E5E7EB]">
                  <div className="flex items-center justify-between mb-[10px] sm:mb-[12px]">
                    <h2 className="text-[14px] sm:text-[16px] font-bold text-[#111827]">All Notifications</h2>
                    <div className="flex items-center gap-[6px] sm:gap-[8px]">
                      <button className="flex items-center gap-[4px] sm:gap-[6px] text-[12px] sm:text-[13px] font-medium
                                         text-[#374151] border border-[#E5E7EB] rounded-[8px] px-[10px] sm:px-[12px]
                                         py-[6px] sm:py-[7px] hover:bg-[#F9FAFB] transition-colors">
                        <IconFilter /><span className="hidden sm:inline">Filter</span>
                      </button>
                      <button className="flex items-center gap-[4px] sm:gap-[6px] text-[12px] sm:text-[13px] font-medium
                                         text-[#374151] border border-[#E5E7EB] rounded-[8px] px-[10px] sm:px-[12px]
                                         py-[6px] sm:py-[7px] hover:bg-[#F9FAFB] transition-colors">
                        <IconSettings /><span className="hidden sm:inline">Settings</span>
                      </button>
                    </div>
                  </div>
                  {/* Scrollable tabs on mobile */}
                  <div className="flex items-center gap-[2px] overflow-x-auto pb-[1px]">
                    {TABS.map(tab => (
                      <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                        className={`text-[12px] sm:text-[13px] font-medium px-[12px] sm:px-[14px] py-[7px] sm:py-[8px]
                                    rounded-t-[6px] whitespace-nowrap transition-colors border-b-2 ${
                          activeTab === tab.id
                            ? "text-[#4F46E5] border-[#4F46E5] bg-[#EEF2FF]"
                            : "text-[#6B7280] border-transparent hover:text-[#374151]"
                        }`}>
                        {tab.label}
                        {tab.id === "all" && unreadCount > 0 && (
                          <span className="ml-[4px] sm:ml-[6px] text-[10px] bg-[#4F46E5] text-white rounded-full px-[5px] sm:px-[6px] py-[1px]">
                            {unreadCount}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Loading */}
                {loading && notifications.length === 0 && (
                  <div className="flex items-center justify-center py-[48px] sm:py-[64px]">
                    <div className="text-center">
                      <svg className="w-8 h-8 animate-spin text-[#4F46E5] mx-auto mb-3" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>
                      <p className="text-[14px] text-[#9CA3AF]">Loading notifications…</p>
                    </div>
                  </div>
                )}

                {/* Error */}
                {error && (
                  <div className="flex items-center justify-center py-[48px] sm:py-[64px]">
                    <div className="text-center">
                      <p className="text-[14px] font-medium text-[#EF4444]">Failed to load notifications</p>
                      <p className="text-[12px] text-[#9CA3AF] mt-[4px]">{error}</p>
                    </div>
                  </div>
                )}

                {/* Empty */}
                {!loading && !error && notifications.length === 0 && (
                  <div className="flex items-center justify-center py-[48px] sm:py-[64px]">
                    <div className="text-center">
                      <div className="w-[48px] h-[48px] bg-[#F3F4F6] rounded-full flex items-center justify-center mx-auto mb-[16px] text-[#9CA3AF]">
                        <IconBell />
                      </div>
                      <p className="text-[14px] font-medium text-[#374151]">No notifications</p>
                      <p className="text-[12px] text-[#9CA3AF] mt-[4px]">You're all caught up!</p>
                    </div>
                  </div>
                )}

                {/* Rows */}
                {notifications.map(n => (
                  <NotificationRow key={n.id} notif={n} onMarkRead={markRead} onDismiss={dismiss} />
                ))}

                {/* Load more */}
                <div className="flex items-center justify-center py-[16px] sm:py-[20px] border-t border-[#F3F4F6]">
                  {hasMore ? (
                    <button onClick={loadMore} disabled={loading}
                      className="flex items-center gap-[6px] text-[13px] font-medium text-[#4F46E5] hover:text-[#4338CA] transition-colors disabled:opacity-50">
                      {loading ? "Loading…" : "Load More Notifications"}
                      <IconChevronDown />
                    </button>
                  ) : (
                    <p className="text-[12px] text-[#9CA3AF]">You've seen all notifications</p>
                  )}
                </div>
              </div>
            </div>

            {/* ── Right sidebar — hidden on mobile, shown xl+ ── */}
            <div className="hidden xl:flex flex-col gap-[16px] w-[300px] 2xl:w-[320px] flex-shrink-0">

              {/* Notification Preferences */}
              <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-[20px] sm:p-[24px]">
                <h3 className="text-[15px] font-bold text-[#111827] flex items-center gap-[8px] mb-[20px]">
                  <span className="text-[#4F46E5]"><IconSettings /></span>
                  Notification Preferences
                </h3>
                <div className="flex flex-col gap-[16px]">
                  {[
                    { label: "Email Notifications", sub: "Receive updates via email",      checked: prefs?.email_enabled ?? true,  toggle: () => updatePrefs({ email_enabled: !(prefs?.email_enabled ?? true)  }) },
                    { label: "Push Notifications",  sub: "Browser notifications",           checked: prefs?.push_enabled  ?? true,  toggle: () => updatePrefs({ push_enabled:  !(prefs?.push_enabled  ?? true)  }) },
                    { label: "SMS Alerts",          sub: "Text message for urgent items",   checked: prefs?.sms_enabled   ?? false, toggle: () => updatePrefs({ sms_enabled:   !(prefs?.sms_enabled   ?? false) }) },
                  ].map(pref => (
                    <div key={pref.label} className="flex items-center justify-between gap-[12px]">
                      <div className="min-w-0">
                        <p className="text-[13px] font-medium text-[#111827]">{pref.label}</p>
                        <p className="text-[11px] text-[#9CA3AF] mt-[2px]">{pref.sub}</p>
                      </div>
                      <Toggle checked={pref.checked} onChange={pref.toggle} />
                    </div>
                  ))}
                </div>
                <button className="w-full mt-[20px] border border-[#E5E7EB] rounded-[8px] py-[9px] text-[13px] font-medium text-[#374151] hover:bg-[#F9FAFB] transition-colors" disabled={saving}>
                  {saving ? "Saving…" : "Manage All Preferences"}
                </button>
              </div>

              {/* Upcoming Deadlines */}
              <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-[20px] sm:p-[24px]">
                <div className="flex items-center gap-[8px] mb-[16px]">
                  <div className="w-[36px] h-[36px] bg-[#FFF7ED] text-[#F97316] rounded-[8px] flex items-center justify-center">
                    <IconCalendar />
                  </div>
                  <div>
                    <h3 className="text-[14px] font-bold text-[#111827]">Upcoming Deadlines</h3>
                    <p className="text-[11px] text-[#9CA3AF]">From your notifications</p>
                  </div>
                </div>
                {deadlines.length === 0 ? (
                  <p className="text-[13px] text-[#9CA3AF]">No deadline notifications</p>
                ) : (
                  <div className="flex flex-col gap-[10px]">
                    {deadlines.map(d => (
                      <div key={d.id} className="bg-white border border-[#E5E7EB] rounded-[10px] px-[14px] py-[12px]">
                        <p className="text-[13px] font-semibold text-[#111827]">{d.title}</p>
                        <p className="text-[12px] text-[#6B7280] mt-[4px]">{d.body.slice(0, 60)}…</p>
                        <span className="inline-block mt-[8px] text-[10px] font-bold px-[8px] py-[3px] rounded-full bg-[#FFF7ED] text-[#C2410C]">
                          Deadline
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                <button onClick={() => setActiveTab("deadline")}
                  className="flex items-center gap-[4px] text-[13px] font-medium text-[#4F46E5] hover:text-[#4338CA] transition-colors mt-[16px]">
                  View All Deadlines <IconChevronDown />
                </button>
              </div>

              {/* Latest News */}
              <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-[20px] sm:p-[24px]">
                <div className="flex items-center gap-[8px] mb-[16px]">
                  <div className="w-[36px] h-[36px] bg-[#F5F3FF] text-[#7C3AED] rounded-[8px] flex items-center justify-center">
                    <IconNewspaper />
                  </div>
                  <h3 className="text-[14px] font-bold text-[#111827]">Latest Immigration News</h3>
                </div>
                {newsItems.length === 0 ? (
                  <p className="text-[13px] text-[#9CA3AF]">No news notifications</p>
                ) : (
                  <div className="flex flex-col">
                    {newsItems.map((item, i) => (
                      <div key={item.id} className={`py-[12px] sm:py-[14px] ${i < newsItems.length - 1 ? "border-b border-[#F3F4F6]" : ""}`}>
                        <div className="flex items-start gap-[10px]">
                          <IconDot />
                          <div>
                            <p className="text-[13px] font-semibold text-[#111827] leading-[18px]">{item.title}</p>
                            <p className="text-[12px] text-[#6B7280] mt-[4px] leading-[16px]">{item.body.slice(0, 70)}…</p>
                            <p className="text-[11px] text-[#9CA3AF] mt-[6px]">
                              {new Date(item.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <button onClick={() => setActiveTab("news")}
                  className="flex items-center gap-[4px] text-[13px] font-medium text-[#4F46E5] hover:text-[#4338CA] transition-colors mt-[4px]">
                  View All News <IconChevronDown />
                </button>
              </div>

              {/* Case Activity */}
              <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-[20px] sm:p-[24px]">
                <div className="flex items-center gap-[8px] mb-[16px]">
                  <div className="w-[36px] h-[36px] bg-[#F0FDF4] text-[#22C55E] rounded-[8px] flex items-center justify-center">
                    <IconTrendingUp />
                  </div>
                  <div>
                    <h3 className="text-[14px] font-bold text-[#111827]">Case Activity</h3>
                    <p className="text-[11px] text-[#9CA3AF]">Recent case updates</p>
                  </div>
                </div>
                <div className="mb-[16px]">
                  <div className="flex items-center justify-between mb-[6px]">
                    <span className="text-[13px] font-medium text-[#111827]">Case Notifications</span>
                    <span className="text-[13px] font-bold text-[#4F46E5]">{caseNotifs.length}</span>
                  </div>
                  <div className="w-full h-[8px] bg-[#E5E7EB] rounded-full overflow-hidden">
                    <div className="h-full bg-[#4F46E5] rounded-full transition-all"
                      style={{ width: caseNotifs.length > 0 ? `${Math.min(100, caseNotifs.length * 20)}%` : "0%" }} />
                  </div>
                </div>
                <div className="flex flex-col gap-[8px]">
                  {[
                    { label: "Unread case updates", value: caseNotifs.filter(n => !n.is_read).length },
                    { label: "Total case activity",  value: caseNotifs.length },
                  ].map(stat => (
                    <div key={stat.label} className="flex items-center justify-between">
                      <span className="text-[12px] text-[#6B7280]">{stat.label}</span>
                      <span className="text-[12px] font-semibold text-[#111827]">{stat.value}</span>
                    </div>
                  ))}
                </div>
                <button onClick={() => setActiveTab("case_update")}
                  className="w-full mt-[16px] bg-[#4F46E5] text-white rounded-[8px] py-[9px] text-[13px] font-medium hover:bg-[#4338CA] transition-colors">
                  View Case Updates
                </button>
              </div>

            </div>
          </div>
        </div>
      </PageContent>
    </div>
  );
}