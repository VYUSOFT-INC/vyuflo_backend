// src/pages/admin/UserManagement.tsx
// Mobile responsive: flex-col on phones, flex-row on tablets+
import { useState } from "react";
import { useAdminCounts, useRecentLogins } from "../../hooks/admin/useDashboard";
import type { RecentLoginUser } from "../../types/admin/dashboard.types";

// ── Icon imports ────────────────────────────────────────────
import imgSearchSmall    from "../../assets/admin/search-small.svg";
import imgExport         from "../../assets/admin/export.svg";
import imgFilter         from "../../assets/admin/filter.svg";
import imgChevronDown    from "../../assets/admin/chevron-down.svg";
import imgChevronLeft    from "../../assets/admin/chevron-left.svg";
import imgChevronRight   from "../../assets/admin/chevron-right.svg";
import imgDotsVertical   from "../../assets/admin/dots-vertical.svg";
import imgPlus           from "../../assets/admin/plus.svg";
import imgUsersTotal     from "../../assets/admin/users-total.svg";
import imgUsersActive    from "../../assets/admin/users-active.svg";
import imgArrowUp        from "../../assets/admin/arrow-up.svg";

const PAGE_SIZE = 20;

const AVATAR_COLORS = [
  "linear-gradient(135deg,#2563eb 0%,#7c3aed 100%)",
  "#a855f7", "#14b8a6", "#f43f5e", "#f59e0b",
  "#10b981", "#6366f1", "#ec4899",
];

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function getAvatarBg(idx: number): string {
  return AVATAR_COLORS[idx % AVATAR_COLORS.length];
}

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <span className="text-[14px] text-[#9ca3af]">—</span>;
  const lower = status.toLowerCase();
  const isActive = lower === "active";
  const isSuspended = lower === "suspended";
  const dot = isActive ? "#22c55e" : isSuspended ? "#ef4444" : "#eab308";
  const bg = isActive ? "#f0fdf4" : isSuspended ? "#fef2f2" : "#fefce8";
  const border = isActive ? "#dcfce7" : isSuspended ? "#fee2e2" : "#fef9c3";
  const color = isActive ? "#15803d" : isSuspended ? "#b91c1c" : "#a16207";
  return (
    <div className="inline-flex items-center gap-[6px] px-[11px] py-[5px] rounded-full"
      style={{ background: bg, border: `1px solid ${border}` }}>
      <div className="rounded-full size-[6px]" style={{ background: dot }} />
      <span className="text-[12px] font-medium whitespace-nowrap leading-[16px]" style={{ color }}>{status}</span>
    </div>
  );
}

function RoleBadge({ role }: { role: string }) {
  return (
    <div className="inline-flex items-center gap-[6px] px-[10px] py-[5px] rounded-[6px] cursor-pointer select-none"
      style={{ border: "1px solid #d1d5db", background: "white" }}>
      <span className="text-[13px] font-medium text-[#374151] leading-[18px] whitespace-nowrap">{role}</span>
      <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
        <path d="M1 1L5 5L9 1" stroke="#9ca3af" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function MetricCardSkeleton() {
  return (
    <div className="relative bg-white rounded-[12px] flex items-start gap-[16px] p-[21px] animate-pulse"
      style={{ border: "1px solid #e5e7eb", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)" }}>
      <div className="size-[48px] rounded-[8px] bg-[#f3f4f6] shrink-0" />
      <div className="flex flex-col gap-[8px] flex-1">
        <div className="h-[14px] w-[80px] rounded bg-[#f3f4f6]" />
        <div className="h-[28px] w-[60px] rounded bg-[#e5e7eb]" />
      </div>
    </div>
  );
}

export default function UserManagement() {
  const [currentPage, setCurrentPage]   = useState(1);
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [search, setSearch]             = useState("");

  const offset = (currentPage - 1) * PAGE_SIZE;
  const { data: counts, isLoading: countsLoading } = useAdminCounts();
  const {
    data: users, total: totalUsers, isLoading: usersLoading,
    error: usersError, refetch: refetchUsers,
  } = useRecentLogins(PAGE_SIZE, offset);

  const totalPages = Math.max(1, Math.ceil(totalUsers / PAGE_SIZE));

  const filtered: RecentLoginUser[] = search.trim()
    ? users.filter((u) =>
        u.full_name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase()) ||
        u.role_name.toLowerCase().includes(search.toLowerCase())
      )
    : users;

  const toggleRow = (i: number) => {
    const next = new Set(selectedRows);
    next.has(i) ? next.delete(i) : next.add(i);
    setSelectedRows(next);
  };

  const toggleAll = () => {
    if (selectedRows.size === filtered.length && filtered.length > 0) setSelectedRows(new Set());
    else setSelectedRows(new Set(filtered.map((_, i) => i)));
  };

  const allSelected = filtered.length > 0 && selectedRows.size === filtered.length;

  const metricCards = [
    {
      label: "Total Users",
      value: countsLoading ? "..." : (counts?.total_users ?? 0).toLocaleString(),
      trend: "+12%", trendBg: "#f0fdf4", trendColor: "#16a34a",
      icon: imgUsersTotal, iconBg: "#eff6ff", arrowImg: imgArrowUp,
    },
    {
      label: "Active Accounts",
      value: countsLoading ? "..." : (counts?.total_active_users ?? 0).toLocaleString(),
      trend: "+8%", trendBg: "#f0fdf4", trendColor: "#16a34a",
      icon: imgUsersActive, iconBg: "#f0fdf4", arrowImg: imgArrowUp,
    },
  ];

  return (
    <div className="min-h-screen bg-[#f9fafb]" style={{ fontFamily: "'Inter', sans-serif" }}>
      <main className="max-w-[1440px] mx-auto px-4 py-6 sm:px-8 sm:py-8 flex flex-col gap-6 sm:gap-8">

        {/* Page Header — STACKS on mobile, ROW on tablet+ */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-[4px]">
            <h1 className="text-xl sm:text-2xl font-bold text-[#111827] leading-tight">User Management</h1>
            <p className="text-xs sm:text-sm text-[#6b7280] leading-[20px]">
              Manage platform access, roles, and visa application statuses.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 sm:gap-3 sm:flex-shrink-0">
            <button
              className="flex items-center gap-2 px-3 sm:px-4 py-2 rounded-[8px] bg-white"
              style={{ border: "1px solid #e5e7eb", boxShadow: "0 1px 1px rgba(0,0,0,0.05)", cursor: "pointer" }}
            >
              <img src={imgExport} alt="" style={{ width: 14, height: 14 }} />
              <span className="text-sm font-medium text-[#374151]">Export</span>
            </button>
            <button
              className="flex items-center gap-2 px-3 sm:px-4 py-2 rounded-[8px] text-white"
              style={{
                backgroundImage: "linear-gradient(135deg,#2563eb 0%,#7c3aed 100%)",
                border: "none", cursor: "pointer",
              }}
            >
              <img src={imgPlus} alt="" style={{ width: 14, height: 14 }} />
              <span className="text-sm font-medium whitespace-nowrap">Create User</span>
            </button>
          </div>
        </div>

        {/* Metric Cards — 1 col phone, 2 col tablet+ */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
          {countsLoading
            ? Array.from({ length: 2 }).map((_, i) => <MetricCardSkeleton key={i} />)
            : metricCards.map((card) => (
                <div key={card.label}
                  className="relative bg-white rounded-[12px] flex items-start gap-4 p-5"
                  style={{ border: "1px solid #e5e7eb", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03)" }}>
                  <div className="size-[48px] rounded-[8px] flex items-center justify-center shrink-0" style={{ background: card.iconBg }}>
                    <img src={card.icon} alt="" style={{ width: 25, height: 20 }} />
                  </div>
                  <div className="flex flex-col gap-[4px] min-w-0">
                    <span className="text-sm font-medium text-[#6b7280] leading-[20px] whitespace-nowrap">{card.label}</span>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-2xl font-bold text-[#111827] leading-[32px]">{card.value}</span>
                      <div className="flex items-center gap-1 px-[6px] py-[2px] rounded-[4px]" style={{ background: card.trendBg }}>
                        <img src={card.arrowImg} alt="" style={{ width: 8, height: 9 }} />
                        <span className="text-xs font-medium leading-[16px]" style={{ color: card.trendColor }}>{card.trend}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
        </div>

        {/* Table Section */}
        <div className="bg-white rounded-[12px] overflow-hidden"
          style={{ border: "1px solid #e5e7eb", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03)" }}>

          {/* Toolbar — STACKS on mobile, ROW on tablet+ */}
          <div className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between" style={{ borderBottom: "1px solid #e5e7eb" }}>
            <div className="relative w-full sm:w-[320px]">
              <div className="flex items-center rounded-[8px] pl-[41px] pr-[13px] py-[10px] bg-white" style={{ border: "1px solid #e5e7eb" }}>
                <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by name, email, or company..."
                  className="w-full outline-none text-sm text-[#111827] placeholder-[#9ca3af] bg-transparent" />
              </div>
              <div className="absolute left-[12px] top-1/2 -translate-y-1/2 pointer-events-none">
                <img src={imgSearchSmall} alt="" style={{ width: 16, height: 16 }} />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button className="flex items-center gap-[6px] px-3 py-2 rounded-[8px] bg-white" style={{ border: "1px solid #e5e7eb", cursor: "pointer" }}>
                <span className="text-sm font-medium text-[#374151] whitespace-nowrap">Change role</span>
                <img src={imgChevronDown} alt="" style={{ width: 10, height: 6 }} />
              </button>
              <button className="flex items-center gap-[6px] px-3 py-2 rounded-[8px] bg-white" style={{ border: "1px solid #e5e7eb", cursor: "pointer" }}>
                <img src={imgFilter} alt="" style={{ width: 14, height: 13 }} />
                <span className="text-sm font-medium text-[#374151]">Filter</span>
              </button>
              <div className="hidden sm:block h-[24px] w-px bg-[#e5e7eb] mx-1" />
              <button className="flex items-center justify-center p-2 rounded-full hover:bg-gray-100 cursor-pointer">
                <img src={imgDotsVertical} alt="" style={{ width: 4, height: 14 }} />
              </button>
            </div>
          </div>

          {/* Table — horizontal scroll on mobile */}
          <div className="overflow-x-auto">
            <table className="w-full border-collapse min-w-[640px]">
              <thead>
                <tr style={{ background: "rgba(249,250,251,0.8)", borderBottom: "1px solid #e5e7eb" }}>
                  <th className="w-[50px] px-4 py-[14px] text-left">
                    <div className="size-[18px] rounded-[4px] cursor-pointer flex items-center justify-center"
                      style={{ border: allSelected ? "2px solid #2563eb" : "1px solid #d1d5db", background: allSelected ? "#2563eb" : "white" }}
                      onClick={toggleAll}>
                      {allSelected && (
                        <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                          <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </div>
                  </th>
                  <th className="px-4 py-[14px] text-left">
                    <span className="text-xs font-semibold text-[#6b7280] tracking-[0.6px] uppercase">USER</span>
                  </th>
                  <th className="w-[160px] px-4 py-[14px] text-left">
                    <span className="text-xs font-semibold text-[#6b7280] tracking-[0.6px] uppercase">ROLE</span>
                  </th>
                  <th className="w-[140px] px-4 py-[14px] text-left">
                    <span className="text-xs font-semibold text-[#6b7280] tracking-[0.6px] uppercase">STATUS</span>
                  </th>
                  <th className="w-[200px] px-4 py-[14px] text-left">
                    <span className="text-xs font-semibold text-[#6b7280] tracking-[0.6px] uppercase">LAST LOGIN</span>
                  </th>
                  <th className="w-[90px] px-4 py-[14px] text-right">
                    <span className="text-xs font-semibold text-[#6b7280] tracking-[0.6px] uppercase">ACTIONS</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {usersLoading ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-[56px] text-center">
                      <div className="flex flex-col items-center gap-3">
                        <div className="size-[32px] rounded-full border-[3px] border-[#e5e7eb] border-t-[#2563eb] animate-spin" />
                        <span className="text-sm text-[#6b7280]">Loading users...</span>
                      </div>
                    </td>
                  </tr>
                ) : usersError ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-[56px] text-center">
                      <div className="flex flex-col items-center gap-2">
                        <span className="text-[28px]">⚠️</span>
                        <span className="text-sm font-medium text-[#b91c1c]">{usersError}</span>
                        <button onClick={refetchUsers} className="mt-2 px-4 py-2 rounded-[8px] text-sm font-medium text-white"
                          style={{ background: "linear-gradient(135deg,#2563eb 0%,#7c3aed 100%)", border: "none", cursor: "pointer" }}>
                          Retry
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-[56px] text-center">
                      <span className="text-sm text-[#6b7280]">No users found.</span>
                    </td>
                  </tr>
                ) : (
                  filtered.map((user, idx) => (
                    <tr key={idx} className="bg-white hover:bg-[#fafafa] transition-colors" style={{ borderTop: "1px solid #f3f4f6" }}>
                      <td className="px-4 py-[18px]">
                        <div className="size-[18px] rounded-[4px] cursor-pointer flex items-center justify-center"
                          style={{ border: selectedRows.has(idx) ? "2px solid #2563eb" : "1px solid #d1d5db", background: selectedRows.has(idx) ? "#2563eb" : "white" }}
                          onClick={() => toggleRow(idx)}>
                          {selectedRows.has(idx) && (
                            <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                              <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-[14px]">
                        <div className="flex items-center gap-3">
                          <div className="size-[38px] rounded-full flex items-center justify-center text-white text-sm font-semibold shrink-0"
                            style={{ background: getAvatarBg(idx), boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }}>
                            {getInitials(user.full_name)}
                          </div>
                          <div className="flex flex-col">
                            <span className="text-sm font-medium text-[#111827] leading-[20px]">{user.full_name}</span>
                            <span className="text-xs text-[#6b7280] leading-[16px]">{user.email}</span>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-[14px]"><RoleBadge role={user.role_name} /></td>
                      <td className="px-4 py-[14px]"><StatusBadge status={user.status} /></td>
                      <td className="px-4 py-[14px]">
                        <span className="text-[13px] text-[#4b5563] leading-[20px] whitespace-nowrap font-mono">{user.last_login ?? "—"}</span>
                      </td>
                      <td className="px-4 py-[14px] text-right">
                        <button className="inline-flex items-center justify-center p-[6px] rounded-[4px] hover:bg-gray-100 cursor-pointer">
                          <img src={imgDotsVertical} alt="" style={{ width: 4, height: 14 }} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination — STACKS on mobile */}
          <div className="flex flex-col gap-3 px-4 py-[14px] sm:flex-row sm:items-center sm:justify-between" style={{ borderTop: "1px solid #e5e7eb" }}>
            <span className="text-xs sm:text-sm text-[#6b7280]">
              {usersLoading ? "Loading..." :
                `Showing ${filtered.length === 0 ? 0 : offset + 1} to ${Math.min(offset + PAGE_SIZE, totalUsers)} of ${totalUsers.toLocaleString()} results`}
            </span>

            <div className="flex items-center gap-1 flex-wrap">
              <button disabled={currentPage === 1} onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="flex items-center gap-[6px] px-3 py-[7px] rounded-[6px]"
                style={{ border: "1px solid #e5e7eb", cursor: currentPage === 1 ? "not-allowed" : "pointer", background: "white", opacity: currentPage === 1 ? 0.45 : 1 }}>
                <img src={imgChevronLeft} alt="" style={{ width: 6, height: 10 }} />
                <span className="text-sm text-[#4b5563]">Prev</span>
              </button>

              {Array.from({ length: Math.min(totalPages, 3) }, (_, i) => i + 1).map((p) => (
                <button key={p} onClick={() => setCurrentPage(p)}
                  className="size-[32px] flex items-center justify-center rounded-[6px] text-sm font-medium"
                  style={{ background: currentPage === p ? "#eff6ff" : "transparent", color: currentPage === p ? "#2563eb" : "#4b5563", border: "none", cursor: "pointer" }}>
                  {p}
                </button>
              ))}

              {totalPages > 3 && (
                <>
                  <span className="size-[32px] flex items-center justify-center text-sm text-[#9ca3af]">...</span>
                  <button onClick={() => setCurrentPage(totalPages)}
                    className="size-[32px] flex items-center justify-center rounded-[6px] text-sm font-medium"
                    style={{ background: currentPage === totalPages ? "#eff6ff" : "transparent", color: currentPage === totalPages ? "#2563eb" : "#4b5563", border: "none", cursor: "pointer" }}>
                    {totalPages}
                  </button>
                </>
              )}

              <button disabled={currentPage === totalPages} onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="flex items-center gap-[6px] px-3 py-[7px] rounded-[6px]"
                style={{ border: "1px solid #e5e7eb", cursor: currentPage === totalPages ? "not-allowed" : "pointer", background: "white", opacity: currentPage === totalPages ? 0.45 : 1 }}>
                <span className="text-sm text-[#4b5563]">Next</span>
                <img src={imgChevronRight} alt="" style={{ width: 6, height: 10 }} />
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
