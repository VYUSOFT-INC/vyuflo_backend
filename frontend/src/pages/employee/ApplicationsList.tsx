// src/pages/employee/ApplicationsList.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApplications } from "../../hooks/employee/useApplications";
import { useCurrentUser } from "../../hooks/useAuth";
import type { Application, ApplicationStatus } from "../../types/employee/application.types";
import { Search, Plus, Bell } from "lucide-react";

// ── Assets ────────────────────────────────────────────────────────────────────
import imgVisaH1b        from "../../assets/icons/applist-visa-h1b.svg";
import imgVisaF1         from "../../assets/icons/applist-visa-f1.svg";
import imgStatusProgress from "../../assets/icons/applist-status-progress.svg";
import imgCheckGreen     from "../../assets/icons/applist-check-green.svg";
import imgChevronSelect  from "../../assets/icons/applist-chevron-select.svg";
import imgChevronRight   from "../../assets/icons/applist-chevron-right.svg";

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatDate(iso: string): { date: string; time: string } {
  try {
    const d = new Date(iso);
    return {
      date: d.toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" }),
      time: d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
    };
  } catch {
    return { date: "—", time: "—" };
  }
}

// ── Status badge config ───────────────────────────────────────────────────────
function getStatusBadge(status: ApplicationStatus) {
  switch (status) {
    case "approved":
      return { bg: "bg-[#ecfdf5]", border: "border border-[#d1fae5]", text: "text-[#047857]", icon: imgCheckGreen,     label: "Approved" };
    case "in_progress":
    case "submitted":
      return { bg: "bg-[#f0f5ff]", border: "border border-[#e5edff]", text: "text-[#2f35ca]", icon: imgStatusProgress, label: "In Progress" };
    case "action_needed":
    case "rfe_response":
      return { bg: "bg-[#fff7ed]", border: "border border-[#fed7aa]", text: "text-[#c2410c]", icon: imgStatusProgress, label: "Action Needed" };
    case "rejected":
      return { bg: "bg-[#fef2f2]", border: "border border-[#fecaca]", text: "text-[#b91c1c]", icon: imgStatusProgress, label: "Rejected" };
    default:
      return { bg: "bg-[#f8fafc]", border: "border border-[#e2e8f0]", text: "text-[#475569]", icon: imgStatusProgress, label: "Draft" };
  }
}

// ── Visa icon ─────────────────────────────────────────────────────────────────
function getVisaIcon(code?: string) {
  if (!code) return imgVisaF1;
  const c = code.toUpperCase();
  if (c.includes("H-1B") || c.includes("H1B")) return imgVisaH1b;
  return imgVisaF1;
}

const PAGE_SIZE = 10;

// ─────────────────────────────────────────────────────────────────────────────
export default function ApplicationsList() {
  const navigate = useNavigate();

  const { data: user } = useCurrentUser();
  const fullName       = user ? `${user.first_name} ${user.last_name}` : "—";
  const userInitials   = user
    ? `${user.first_name[0] ?? ""}${user.last_name[0] ?? ""}`.toUpperCase()
    : "?";

  // ── Filter / sort / search state ──────────────────────────────────────────
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "">("");
  const [visaFilter,   setVisaFilter]   = useState("");
  const [sortBy,       setSortBy]       = useState("newest");
  const [search,       setSearch]       = useState("");
  const [page,         setPage]         = useState(1);

  // ── Data ──────────────────────────────────────────────────────────────────
  const { data, isLoading, error } = useApplications({
    status: statusFilter || undefined,
    limit:  200,
    offset: 0,
  });

  const allItems: Application[] = data?.items ?? [];

  const filtered = allItems.filter(a => {
    const q           = search.toLowerCase();
    const matchSearch = !q ||
      a.application_number?.toLowerCase().includes(q) ||
      a.visa_type?.name?.toLowerCase().includes(q) ||
      a.sponsor_employer?.toLowerCase().includes(q);
    const matchVisa   = !visaFilter || a.visa_type?.code === visaFilter;
    return matchSearch && matchVisa;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === "oldest")
      return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });

  const totalPages  = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const paginated   = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const showingFrom = sorted.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const showingTo   = Math.min(page * PAGE_SIZE, sorted.length);

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden" style={{ fontFamily: "Inter, sans-serif" }}>

      {/* ══════════════════════════════════════════════════════════════════════
          TOP HEADER — Figma node 14:12666
          h-[72px], bg-[rgba(255,255,255,0.8)], border-b border-[#f1f5f9]
          Left:  "Applications" title + subtitle
          Right: Search input + Bell button + "+ New Application" CTA
      ══════════════════════════════════════════════════════════════════════ */}
      <header className="bg-[rgba(255,255,255,0.8)] border-b border-[#f1f5f9] backdrop-blur-sm
                         flex h-[72px] items-center justify-between px-[32px] shrink-0 sticky top-0 z-10">

        {/* Left: title + subtitle — w-[248px] */}
        <div className="flex flex-col gap-[2px]">
          <p className="font-bold leading-[28px] text-[#0f172a] text-[20px] tracking-[-0.5px] whitespace-nowrap">
            Applications
          </p>
          <p className="font-normal leading-[16px] text-[#64748b] text-[12px] tracking-[-0.5px] whitespace-nowrap">
            Manage and track all your visa applications.
          </p>
        </div>

        {/* Right: search + bell + CTA — gap-[16px], h-[40px] */}
        <div className="flex items-center gap-[16px] h-[40px]">

          {/* Search input — bg-[#f8fafc], border-[#e2e8f0], rounded-[12px], h-[38px], w-[256px] */}
          <div className="relative h-[38px] w-[256px]">
            <input
              type="text"
              placeholder="Search applications..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
              className="bg-[#f8fafc] border border-[#e2e8f0] h-[38px] w-[256px]
                         pl-[36px] pr-[16px] py-[8px] rounded-[12px]
                         text-[#1e293b] text-[14px] font-normal tracking-[-0.5px]
                         focus:outline-none focus:ring-2 focus:ring-[#5269f2] focus:border-transparent
                         placeholder:text-[#94a3b8] transition-colors"
            />
            <Search
              size={14}
              className="absolute left-[12px] top-1/2 -translate-y-1/2 text-[#94a3b8] pointer-events-none"
            />
          </div>

          {/* Bell button — bg-white, border-[#e2e8f0], drop-shadow, rounded-[12px], size-[40px] */}
          <button
            type="button"
            onClick={() => navigate("/notifications")}
            aria-label="Notifications"
            className="bg-white border border-[#e2e8f0] drop-shadow-[0px_1px_1px_rgba(0,0,0,0.05)]
                       flex items-center justify-center relative rounded-[12px] shrink-0 size-[40px]
                       hover:bg-[#f8fafc] transition-colors"
          >
            <Bell size={14} className="text-[#64748b]" />
            {/* Notification dot — bg-[#5269f2] */}
            <span className="absolute bg-[#5269f2] border border-white h-[8px] w-[8px]
                             rounded-full top-[8px] right-[10px]" />
          </button>

          {/* + New Application — gradient, rounded-[12px], h-[36px], w-[162px] */}
          <button
            type="button"
            onClick={() => navigate("/applications/new")}
            className="drop-shadow-[0px_1px_1px_rgba(0,0,0,0.05)] flex items-center gap-[8px]
                       h-[36px] justify-center px-[16px] py-[8px] rounded-[12px] shrink-0
                       text-white text-[14px] font-medium tracking-[-0.5px] leading-[20px]
                       hover:opacity-90 transition-opacity"
            style={{ backgroundImage: "linear-gradient(167.47deg, rgb(58,70,229) 0%, rgb(157,78,221) 100%)" }}
          >
            <Plus size={12} />
            New Application
          </button>
        </div>
      </header>

      {/* ══════════════════════════════════════════════════════════════════════
          SCROLLABLE CONTENT
      ══════════════════════════════════════════════════════════════════════ */}
      <main className="flex-1 overflow-y-auto pb-[48px] pt-[32px] px-[32px]">
        <div className="flex flex-col gap-[24px] w-full">

          {/* ── Filter bar ────────────────────────────────────────────────── */}
          <div className="bg-white border border-[#f1f5f9] drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)]
                          flex flex-wrap gap-[16px] items-center p-[17px] rounded-[16px] w-full">

            {/* Status filter */}
            <div className="flex items-center gap-[8px] h-[37px]">
              <span className="text-[#334155] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
                Status:
              </span>
              <div className="relative">
                <select
                  value={statusFilter}
                  onChange={e => { setStatusFilter(e.target.value as ApplicationStatus | ""); setPage(1); }}
                  className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[8px] h-[37px] pl-[8px] pr-[32px]
                             text-[#334155] text-[14px] tracking-[-0.5px] appearance-none
                             focus:outline-none focus:border-[#3a46e5] cursor-pointer"
                  style={{ fontFamily: "Inter, sans-serif" }}
                >
                  <option value="">All Statuses</option>
                  <option value="draft">Draft</option>
                  <option value="in_progress">In Progress</option>
                  <option value="action_needed">Action Needed</option>
                  <option value="submitted">Submitted</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                </select>
                <img src={imgChevronSelect} alt="" className="w-[21px] h-[21px] object-contain absolute right-[6px] top-[8px] pointer-events-none" />
              </div>
            </div>

            {/* Visa Type filter */}
            <div className="flex items-center gap-[8px] h-[37px]">
              <span className="text-[#334155] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
                Visa Type:
              </span>
              <div className="relative">
                <select
                  value={visaFilter}
                  onChange={e => { setVisaFilter(e.target.value); setPage(1); }}
                  className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[8px] h-[37px] pl-[8px] pr-[32px]
                             text-[#334155] text-[14px] tracking-[-0.5px] appearance-none
                             focus:outline-none focus:border-[#3a46e5] cursor-pointer"
                  style={{ fontFamily: "Inter, sans-serif" }}
                >
                  <option value="">All Types</option>
                  <option value="H-1B">H-1B</option>
                  <option value="F-1">F-1</option>
                  <option value="F-1 OPT">F-1 OPT</option>
                  <option value="O-1A">O-1A</option>
                  <option value="L-1">L-1</option>
                  <option value="EB-2">EB-2</option>
                </select>
                <img src={imgChevronSelect} alt="" className="w-[21px] h-[21px] object-contain absolute right-[6px] top-[8px] pointer-events-none" />
              </div>
            </div>

            {/* Sort by */}
            <div className="flex items-center gap-[8px] h-[37px]">
              <span className="text-[#334155] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
                Sort by:
              </span>
              <div className="relative">
                <select
                  value={sortBy}
                  onChange={e => { setSortBy(e.target.value); setPage(1); }}
                  className="bg-white border border-[#e2e8f0] rounded-[8px] h-[37px] pl-[8px] pr-[32px]
                             text-[#334155] text-[14px] tracking-[-0.5px] appearance-none
                             focus:outline-none focus:border-[#3a46e5] cursor-pointer"
                  style={{ fontFamily: "Inter, sans-serif" }}
                >
                  <option value="newest">Date Modified (Newest)</option>
                  <option value="oldest">Date Modified (Oldest)</option>
                </select>
                <img src={imgChevronSelect} alt="" className="w-[21px] h-[21px] object-contain absolute right-[6px] top-[8px] pointer-events-none" />
              </div>
            </div>
          </div>

          {/* ── Table card ────────────────────────────────────────────────── */}
          <div className="bg-white border border-[#f1f5f9] overflow-hidden rounded-[24px]
                          shadow-[0px_4px_12px_0px_rgba(0,0,0,0.02)] w-full">

            {/* Loading */}
            {isLoading && (
              <div className="flex items-center justify-center py-[64px]">
                <svg className="w-8 h-8 animate-spin text-[#3a46e5]" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              </div>
            )}

            {/* Error */}
            {error && !isLoading && (
              <div className="flex items-center justify-center py-[64px]">
                <div className="text-center">
                  <p className="text-[#ef4444] text-[16px] font-medium mb-[4px]">Failed to load applications</p>
                  <p className="text-[#64748b] text-[14px]">{error}</p>
                </div>
              </div>
            )}

            {/* Table */}
            {!isLoading && !error && (
              <>
                {/* Table header row */}
                <div className="bg-[#f8fafc] border-b border-[#f1f5f9]
                                grid grid-cols-[1.2fr_1fr_1fr_1fr_80px] h-[50px] items-center px-[24px]">
                  <span className="text-[#334155] text-[12px] font-semibold tracking-[-0.5px] leading-[16px]">Applicant / ID</span>
                  <span className="text-[#334155] text-[12px] font-semibold tracking-[-0.5px] leading-[16px]">Visa Category</span>
                  <span className="text-[#334155] text-[12px] font-semibold tracking-[-0.5px] leading-[16px]">Submission Date</span>
                  <span className="text-[#334155] text-[12px] font-semibold tracking-[-0.5px] leading-[16px]">Status</span>
                  <span className="text-[#334155] text-[12px] font-semibold tracking-[-0.5px] leading-[16px] text-right">Action</span>
                </div>

                {/* Data rows */}
                {paginated.length > 0 ? (
                  paginated.map((app, i) => {
                    const badge    = getStatusBadge(app.status);
                    const visaIcon = getVisaIcon(app.visa_type?.code);
                    const dt       = formatDate(app.submission_date ?? app.created_at);

                    return (
                      <div
                        key={app.id}
                        onClick={() => navigate(`/applications/${app.id}`)}
                        className={`cursor-pointer hover:bg-[#f8fafc] transition-colors
                                    ${i > 0 ? "border-t border-[#f1f5f9]" : ""}`}
                      >
                        {/* ── Mobile card (< sm) ── */}
                        <div className="flex sm:hidden items-start gap-[12px] px-[16px] py-[14px]">
                          <div className="bg-[#f0f5ff] flex items-center justify-center rounded-full shrink-0 size-[40px]">
                            <span className="text-[#3a46e5] text-[14px] font-bold tracking-[-0.5px]">{userInitials}</span>
                          </div>
                          <div className="flex-1 min-w-0 flex flex-col gap-[6px]">
                            <div className="flex items-center justify-between gap-[8px]">
                              <div className="min-w-0">
                                <p className="text-[#0f172a] text-[14px] font-bold tracking-[-0.5px] truncate">{fullName}</p>
                                <p className="text-[#64748b] text-[11px] tracking-[-0.5px]">{app.application_number}</p>
                              </div>
                              <img src={imgChevronRight} alt="" className="w-[8px] h-[12px] shrink-0" />
                            </div>
                            <div className="flex items-center justify-between gap-[8px]">
                              <div className="flex items-center gap-[5px] min-w-0">
                                <img src={visaIcon} alt="" className="w-[12px] h-[12px] shrink-0" />
                                <span className="text-[#334155] text-[12px] font-medium tracking-[-0.5px] truncate">
                                  {app.visa_type?.name ?? "—"}
                                </span>
                              </div>
                              <span className={`${badge.bg} ${badge.border} ${badge.text}
                                               inline-flex items-center gap-[5px] shrink-0
                                               px-[8px] py-[3px] rounded-[6px]
                                               text-[11px] font-medium whitespace-nowrap`}>
                                <img src={badge.icon} alt="" className="w-[8px] h-[9px]" />
                                {badge.label}
                              </span>
                            </div>
                            <p className="text-[#94a3b8] text-[11px] tracking-[-0.5px]">{dt.date} · {dt.time}</p>
                          </div>
                        </div>

                        {/* ── Desktop table row (sm+) ── */}
                        <div className="hidden sm:grid sm:grid-cols-[1.2fr_1fr_1fr_80px] lg:grid-cols-[1.2fr_1fr_1fr_1fr_80px]
                                        min-h-[64px] items-center py-[8px] px-[24px]">
                          <div className="flex items-center gap-[12px]">
                            <div className="bg-[#f0f5ff] flex items-center justify-center rounded-full shrink-0 size-[40px]">
                              <span className="text-[#3a46e5] text-[14px] font-bold tracking-[-0.5px]">{userInitials}</span>
                            </div>
                            <div className="flex flex-col gap-[2px]">
                              <span className="text-[#0f172a] text-[14px] font-bold tracking-[-0.5px] whitespace-nowrap">{fullName}</span>
                              <span className="text-[#64748b] text-[12px] tracking-[-0.5px] whitespace-nowrap">{app.application_number}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-[8px]">
                            <img src={visaIcon} alt="" className="w-[14px] h-[14px] shrink-0" />
                            <span className="text-[#334155] text-[14px] font-medium tracking-[-0.5px] whitespace-nowrap">
                              {app.visa_type?.name ?? "—"}
                            </span>
                          </div>
                          <div className="flex flex-col gap-[2px]">
                            <span className="text-[#0f172a] text-[14px] font-medium tracking-[-0.5px] whitespace-nowrap">{dt.date}</span>
                            <span className="text-[#64748b] text-[12px] tracking-[-0.5px] whitespace-nowrap">{dt.time}</span>
                          </div>
                          <div>
                            <span className={`${badge.bg} ${badge.border} ${badge.text}
                                             inline-flex items-center gap-[6px] h-[26px]
                                             pl-[11px] pr-[10px] rounded-[6px]
                                             text-[12px] font-medium tracking-[-0.5px] whitespace-nowrap`}>
                              <img src={badge.icon} alt="" className="w-[9px] h-[10px] shrink-0" />
                              {badge.label}
                            </span>
                          </div>
                          <div className="flex items-center justify-end">
                            <button type="button"
                              onClick={e => { e.stopPropagation(); navigate(`/applications/${app.id}`); }}
                              className="flex items-center justify-center w-[25px] h-[36px] rounded-[8px] hover:bg-[#f1f5f9] transition-colors">
                              <img src={imgChevronRight} alt="→" className="w-[8.75px] h-[14px]" />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  /* Empty state */
                  <div className="flex flex-col items-center justify-center py-[64px] text-center">
                    <p className="text-[#334155] text-[16px] font-semibold mb-[4px]">No applications found</p>
                    <p className="text-[#94a3b8] text-[14px]">
                      {search || statusFilter || visaFilter
                        ? "Try adjusting your filters"
                        : "Click 'New Application' to get started"}
                    </p>
                    <button
                      type="button"
                      onClick={() => navigate("/applications/new")}
                      className="mt-[16px] flex items-center gap-[6px] px-[16px] py-[8px]
                                 rounded-[12px] text-white text-[14px] font-medium
                                 hover:opacity-90 transition-opacity"
                      style={{ backgroundImage: "linear-gradient(167.47deg, rgb(58,70,229) 0%, rgb(157,78,221) 100%)" }}
                    >
                      <Plus size={12} />
                      New Application
                    </button>
                  </div>
                )}

                {/* Pagination footer */}
                <div className="bg-[rgba(248,250,252,0.5)] border-t border-[#f1f5f9]
                                flex items-center justify-between h-[67px] px-[24px]">
                  <p className="text-[14px] tracking-[-0.5px] leading-[20px]">
                    <span className="text-[#64748b] font-normal">Showing </span>
                    <span className="text-[#0f172a] font-medium">{showingFrom}</span>
                    <span className="text-[#64748b] font-normal"> to </span>
                    <span className="text-[#0f172a] font-medium">{showingTo}</span>
                    <span className="text-[#64748b] font-normal"> of </span>
                    <span className="text-[#0f172a] font-medium">{sorted.length}</span>
                    <span className="text-[#64748b] font-normal"> applications</span>
                  </p>
                  <div className="flex items-center gap-[8px]">
                    <button
                      type="button"
                      disabled={page <= 1}
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      className="bg-white border border-[#e2e8f0] flex items-center justify-center
                                 h-[34px] px-[12px] rounded-[8px] text-[#64748b] text-[14px]
                                 font-medium tracking-[-0.5px] leading-[20px]
                                 disabled:opacity-50 disabled:cursor-not-allowed
                                 hover:bg-[#f8fafc] transition-colors"
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      disabled={page >= totalPages}
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      className="bg-white border border-[#e2e8f0] flex items-center justify-center
                                 h-[34px] px-[12px] rounded-[8px] text-[#64748b] text-[14px]
                                 font-medium tracking-[-0.5px] leading-[20px]
                                 disabled:opacity-50 disabled:cursor-not-allowed
                                 hover:bg-[#f8fafc] transition-colors"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}