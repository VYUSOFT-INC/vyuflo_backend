// src/pages/employee/Dashboard.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCurrentUser } from "../../hooks/useAuth";
import { useDashboard } from "../../hooks/employee/useDashboard";
import type { ActivityItem } from "../../types/employee/dashboard.types";

import imgKpi1       from "../../assets/icons/kpi-apps.svg";
import imgKpi2       from "../../assets/icons/kpi-docs.svg";
import imgKpi3       from "../../assets/icons/kpi-clock.svg";
import imgKpi4       from "../../assets/icons/kpi-sponsor.svg";
import imgTrend      from "../../assets/icons/trend-up.svg";
import imgClockSm    from "../../assets/icons/clock-small.svg";
import imgVerified   from "../../assets/icons/verified-badge.svg";
import imgContIcon   from "../../assets/icons/continue-draft.svg";
import imgStartIcon  from "../../assets/icons/start-new.svg";
import imgArrowRight from "../../assets/icons/arrow-right-dash.svg";
import imgGuide1     from "../../assets/icons/guide-lca.svg";
import imgGuide2     from "../../assets/icons/guide-degree.svg";
import imgGuide3     from "../../assets/icons/guide-photo.svg";
import imgGuide4     from "../../assets/icons/guide-fees.svg";
import imgMoreDots   from "../../assets/icons/more-dots.svg";
import imgDonut      from "../../assets/icons/donut-chart.svg";
import imgDotFilled  from "../../assets/icons/dot-filled.svg";
import imgDotEmpty   from "../../assets/icons/dot-empty.svg";
import { PageContent, PageHeader } from "../../components/layout/Pageheader";

// ── Static guidance items ─────────────────────────────────────────────────────
const GUIDANCE = [
  { id: "1", icon: imgGuide1, tag: "Required", tagBg: "bg-[#e5edff]",              tagText: "text-[#2f35ca]", title: "LCA Overview",       desc: "Understanding the Labor Condition Application process and timelines." },
  { id: "2", icon: imgGuide2, tag: "Optional", tagBg: "bg-[rgba(157,78,221,0.1)]", tagText: "text-[#9d4edd]", title: "Degree Evaluation",  desc: "When and how to get your foreign degree evaluated for US equivalent." },
  { id: "3", icon: imgGuide3, tag: "Tip",      tagBg: "bg-[#e2e8f0]",              tagText: "text-[#334155]", title: "Photo Requirements", desc: "USCIS passport-style photo specifications and common mistakes." },
  { id: "4", icon: imgGuide4, tag: "Info",     tagBg: "bg-[#e2e8f0]",              tagText: "text-[#334155]", title: "Filing Fees 2024",   desc: "Updated fee schedule for I-129 and premium processing." },
];

// ── Static activity fallback ──────────────────────────────────────────────────
const ACTIVITY_FALLBACK: ActivityItem[] = [
  { id: "1", title: "Uploaded Passport Copy",  description: "Document requires verification", timestamp: new Date().toISOString(),                            color: "#5269f2" },
  { id: "2", title: "Draft Saved",             description: "H-1B Application Form",          timestamp: new Date(Date.now() - 86400000).toISOString(),        color: "#10b981" },
  { id: "3", title: "Profile Created",         description: "Basic setup completed",          timestamp: new Date(Date.now() - 86400000 + 900000).toISOString(), color: "#cbd5e1" },
  { id: "4", title: "Account Registered",      description: "Welcome to VisaFlow",            timestamp: new Date(Date.now() - 86400000 + 600000).toISOString(), color: "#cbd5e1" },
];

function formatTs(iso: string): string {
  try {
    const d    = new Date(iso);
    const diff = Date.now() - d.getTime();
    const days = Math.floor(diff / 86400000);
    const time = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
    if (days === 0) return `Today, ${time}`;
    if (days === 1) return `Yesterday, ${time}`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch { return iso; }
}

// ─────────────────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const navigate                  = useNavigate();
  const { data: user }            = useCurrentUser();
  const { data: dash, isLoading } = useDashboard();
  const [search, setSearch]       = useState("");

  const firstName = user?.first_name ?? "Alexandra";

  // KPI values
  const s               = dash?.stats;
  const activeApps      = s?.active_applications       ?? 1;
  const docsVerified    = s?.documents_verified        ?? 4;
  const docsTotal       = s?.documents_total           ?? 12;
  const docsAction      = s?.documents_action_required ?? 2;
  const procDays        = s?.processing_days           ?? 45;
  const procType        = s?.processing_type           ?? "Standard Processing";
  const sponsorName     = s?.sponsor_name              ?? "TechCorp Inc.";
  const sponsorStage    = s?.sponsor_stage             ?? "LCA Filed";
  const sponsorVerified = s?.sponsor_verified          ?? true;
  const readiness       = s?.profile_readiness         ?? 75;
  const docsBarW        = docsTotal > 0 ? Math.round((docsVerified / docsTotal) * 100) : 33;

  const activity = (dash?.activity ?? []).length > 0
    ? (dash?.activity ?? [])
    : ACTIVITY_FALLBACK;

  return (
    // ── Full page: header + scrollable content ──────────────────────────────
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden" style={{ fontFamily: "Inter, sans-serif" }}>

      {/* ══════════════════════════════════════════════════════════════════════
          TOP HEADER  — Figma node 14:12890
          h-[72px], bg-[rgba(255,255,255,0.8)], border-b border-[#f1f5f9]
          flex, items-center, justify-between, px-[32px]
      ══════════════════════════════════════════════════════════════════════ */}
      <PageHeader
        title="Dashboard Overview"
        subtitle={`Welcome back, ${firstName}. Here's your visa status.`}
        showSearch
        searchValue={search}
        searchPlaceholder="Search applications..."
        onSearchChange={setSearch}
      />
      <PageContent>
        <div className="flex flex-col gap-[32px] w-full max-w-[1200px]">

          {/* ── STATUS OVERVIEW ROW ─────────────────────────────────────────
              Figma: flex, gap-[24px], h-[165px], 4 cards each w-[261px]
          ──────────────────────────────────────────────────────────────────*/}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-[24px]">

            {/* Card 1: Active Applications */}
            <div className="bg-white border border-[#f1f5f9] flex flex-col gap-[16px] h-[165px]
                            items-start overflow-clip pb-[40px] pt-[25px] px-[25px] relative
                            rounded-[24px] shadow-[0px_4px_12px_0px_rgba(0,0,0,0.02)]">
              <p className="font-medium leading-[20px] text-[#64748b] text-[14px] tracking-[-0.5px] whitespace-nowrap">
                Active Applications
              </p>
              <p className="font-bold leading-[36px] text-[#0f172a] text-[30px] tracking-[-0.5px]">
                {isLoading ? "—" : activeApps}
              </p>
              <div className="bg-[#ecfdf5] flex gap-[8px] h-[24px] items-center px-[10px] py-[4px] rounded-[6px] shrink-0">
                <img src={imgTrend} alt="" className="w-[13.5px] h-[12px] object-contain shrink-0" />
                <span className="font-medium text-[#059669] text-[12px] tracking-[-0.5px] leading-[16px] whitespace-nowrap">
                  In Progress
                </span>
              </div>
              <div className="absolute flex flex-col h-[88px] items-start left-[170.5px] opacity-10 p-[24px] right-[-0.5px] top-0 pointer-events-none">
                <img src={imgKpi1} alt="" className="w-[40.5px] h-[36px] object-contain" />
              </div>
            </div>

            {/* Card 2: Documents Verified */}
            <div className="bg-white border border-[#f1f5f9] flex flex-col gap-[8px] h-[165px]
                            items-start overflow-clip pb-[34px] pt-[25px] px-[25px] relative
                            rounded-[24px] shadow-[0px_4px_12px_0px_rgba(0,0,0,0.02)]">
              <p className="font-medium leading-[20px] text-[#64748b] text-[14px] tracking-[-0.5px] whitespace-nowrap">
                Documents Verified
              </p>
              <p className="font-bold leading-[36px] text-[#0f172a] text-[30px] tracking-[-0.5px]">
                {isLoading ? "—" : `${docsVerified}/${docsTotal}`}
              </p>
              {/* Progress bar */}
              <div className="bg-[#f1f5f9] h-[6px] rounded-full shrink-0 w-[211px] overflow-hidden">
                <div className="bg-[#5269f2] h-[6px] rounded-full" style={{ width: `${docsBarW}%` }} />
              </div>
              <p className="font-normal leading-[16px] text-[#64748b] text-[12px] tracking-[-0.5px] whitespace-nowrap">
                Action required on {docsAction} items
              </p>
              <div className="absolute flex flex-col h-[88px] items-start left-[170.5px] opacity-10 p-[24px] right-[-0.5px] top-0 pointer-events-none">
                <img src={imgKpi2} alt="" className="w-[40.5px] h-[36px] object-contain" />
              </div>
            </div>

            {/* Card 3: Est. Processing Time */}
            <div className="bg-white border border-[#f1f5f9] flex flex-col gap-[16px] h-[165px]
                            items-start overflow-clip pb-[37px] pt-[25px] px-[25px] relative
                            rounded-[24px] shadow-[0px_4px_12px_0px_rgba(0,0,0,0.02)]">
              <p className="font-medium leading-[20px] text-[#64748b] text-[14px] tracking-[-0.5px] whitespace-nowrap">
                Est. Processing Time
              </p>
              <p className="leading-none text-[0px] whitespace-nowrap">
                <span className="font-bold leading-[36px] text-[#0f172a] text-[30px] tracking-[-0.5px]">
                  {isLoading ? "—" : `${procDays} `}
                </span>
                <span className="leading-[36px] text-[#94a3b8] text-[18px]">days</span>
              </p>
              <div className="bg-[#f8fafc] border border-[#f1f5f9] flex gap-[8px] h-[26px] items-center px-[11px] py-[5px] rounded-[6px] shrink-0">
                <img src={imgClockSm} alt="" className="size-[12px] object-contain shrink-0" />
                <span className="font-medium text-[#64748b] text-[12px] tracking-[-0.5px] leading-[16px] whitespace-nowrap">
                  {procType}
                </span>
              </div>
              <div className="absolute flex flex-col h-[88px] items-start left-[179.5px] opacity-10 p-[24px] right-[-0.5px] top-0 pointer-events-none">
                <img src={imgKpi3} alt="" className="w-[31.5px] h-[36px] object-contain" />
              </div>
            </div>

            {/* Card 4: Sponsor Status */}
            <div className="bg-white border border-[#f1f5f9] flex flex-col gap-[8px] h-[165px]
                            items-start overflow-clip p-[25px] relative rounded-[24px]
                            shadow-[0px_4px_12px_0px_rgba(0,0,0,0.02)]">
              <p className="font-medium leading-[20px] text-[#64748b] text-[14px] tracking-[-0.5px] whitespace-nowrap">
                Sponsor Status
              </p>
              <p className="font-bold leading-[23px] text-[#0f172a] text-[18px] tracking-[-0.5px] whitespace-nowrap">
                {isLoading ? "—" : sponsorName}
              </p>
              <p className="font-normal leading-[20px] text-[#64748b] text-[14px] tracking-[-0.5px] whitespace-nowrap">
                {sponsorStage}
              </p>
              {sponsorVerified && (
                <div className="bg-[#f0f5ff] flex gap-[8px] h-[24px] items-center px-[10px] py-[4px] rounded-[6px] shrink-0">
                  <img src={imgVerified} alt="" className="size-[12px] object-contain shrink-0" />
                  <span className="font-medium text-[#2f35ca] text-[12px] tracking-[-0.5px] leading-[16px] whitespace-nowrap">
                    Verified
                  </span>
                </div>
              )}
              <div className="absolute flex flex-col h-[88px] items-start left-[166px] opacity-10 p-[24px] right-0 top-0 pointer-events-none">
                <img src={imgKpi4} alt="" className="w-[45px] h-[36px] object-contain" />
              </div>
            </div>
          </div>

          {/* ── TWO COLUMN ROW ──────────────────────────────────────────────
              Figma: flex, gap-[32px], left col w-[733px], right col w-[351px]
          ──────────────────────────────────────────────────────────────────*/}
          <div className="flex flex-col xl:flex-row gap-[32px] items-start w-full">

            {/* LEFT column — w-[733px] */}
            <div className="flex flex-col gap-[32px] w-full xl:flex-1">

              {/* QUICK ACTIONS ─────────────────────────────────────────────
                  Figma: bg-white, border-[#f1f5f9], drop-shadow, rounded-[24px],
                  gap-[24px], h-[257px], p-[33px]
              ────────────────────────────────────────────────────────────── */}
              <div className="bg-white border border-[#f1f5f9] drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)]
                              flex flex-col gap-[24px] items-start p-[33px] rounded-[24px] w-full">
                <p className="font-bold leading-[28px] text-[#0f172a] text-[18px] tracking-[-0.5px] whitespace-nowrap">
                  Quick Actions
                </p>

                <div className="flex flex-col sm:flex-row gap-[16px] w-full">

                  {/* Continue Draft — bg-[#f0f5ff], border-[#cddbfe], w-[326px] */}
                  <button
                    type="button"
                    onClick={() => navigate("/applications/list")}
                    className="bg-[#f0f5ff] border border-[#cddbfe] flex gap-[16px] h-[139px]
                               items-start overflow-clip pb-[47px] pl-[21px] pr-[21px] pt-[21px]
                               relative rounded-[16px] flex-1 text-left
                               hover:bg-[#e8eeff] transition-colors cursor-pointer"
                  >
                    <div className="bg-white drop-shadow-[0px_1px_1px_rgba(0,0,0,0.05)] flex items-center
                                    justify-center px-[15px] py-[10px] rounded-[12px] shrink-0 size-[48px]">
                      <img src={imgContIcon} alt="" className="size-[18px] object-contain" />
                    </div>
                    <div className="flex flex-col gap-[12px] items-start">
                      <p className="font-bold leading-[24px] text-[#242b81] text-[16px] tracking-[-0.5px] whitespace-nowrap">
                        Continue Draft
                      </p>
                      <p className="font-normal leading-[16px] text-[12px] text-[rgba(47,53,202,0.8)] tracking-[-0.5px] whitespace-nowrap">
                        H-1B Specialty Occupation
                      </p>
                      {/* Progress bar */}
                      <div className="flex gap-[8px] items-center">
                        <div className="bg-white h-[6px] rounded-full w-[100px] overflow-hidden">
                          <div className="bg-[#5269f2] h-[6px] rounded-full w-[45px]" />
                        </div>
                        <span className="font-semibold text-[#3a46e5] text-[10px] tracking-[-0.5px] leading-[15px] whitespace-nowrap">
                          45%
                        </span>
                      </div>
                    </div>
                    {/* Gradient deco */}
                    <div
                      className="absolute h-[96px] left-[275.66px] opacity-5 right-[-47.66px] rounded-bl-full top-[-48px]"
                      style={{ backgroundImage: "linear-gradient(135deg, rgb(58,70,229) 0%, rgb(157,78,221) 100%)" }}
                    />
                  </button>

                  {/* Start New Application — bg-white, border-[#e2e8f0], w-[326px] */}
                  <button
                    type="button"
                    onClick={() => navigate("/applications/new")}
                    className="bg-white border border-[#e2e8f0] flex gap-[16px] h-[139px]
                               items-start p-[21px] rounded-[16px] flex-1 text-left
                               hover:bg-[#f8fafc] transition-colors cursor-pointer"
                  >
                    <div className="bg-[#f1f5f9] flex items-center justify-center px-[16px] py-[10px] rounded-[12px] shrink-0 size-[48px]">
                      <img src={imgStartIcon} alt="" className="w-[15.75px] h-[18px] object-contain" />
                    </div>
                    <div className="flex flex-col gap-[12px] items-start">
                      <p className="font-bold leading-[24px] text-[#0f172a] text-[16px] tracking-[-0.5px] whitespace-nowrap">
                        Start New Application
                      </p>
                      <p className="font-normal text-[#64748b] text-[12px] tracking-[-0.5px] leading-[20px]">
                        Begin a new visa or green card{"\n"}process.
                      </p>
                      <div className="flex gap-[4px] items-center">
                        <span className="font-medium leading-[16px] text-[#3a46e5] text-[12px] tracking-[-0.5px] whitespace-nowrap">
                          Start now{" "}
                        </span>
                        <img src={imgArrowRight} alt="" className="w-[8.75px] h-[10px] object-contain" />
                      </div>
                    </div>
                  </button>
                </div>
              </div>

              {/* GUIDANCE LIBRARY ──────────────────────────────────────────
                  Figma: bg-white, border-[#f1f5f9], drop-shadow, rounded-[24px],
                  gap-[24px], h-[522px], p-[33px]
              ────────────────────────────────────────────────────────────── */}
              <div className="bg-white border border-[#f1f5f9] drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)]
                              flex flex-col gap-[24px] items-start p-[33px] rounded-[24px] w-full">

                {/* Header row */}
                <div className="flex items-center justify-between w-full">
                  <div className="flex flex-col gap-[4px]">
                    <p className="font-bold leading-[28px] text-[#0f172a] text-[18px] tracking-[-0.5px] whitespace-nowrap">
                      H-1B Guidance Library
                    </p>
                    <p className="font-normal leading-[20px] text-[#64748b] text-[14px] tracking-[-0.5px] whitespace-nowrap">
                      Resources tailored to your target visa.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="flex h-[32px] items-center justify-center px-[12px] rounded-[8px] hover:bg-[#f0f5ff] transition-colors"
                  >
                    <span className="font-medium leading-[20px] text-[#3a46e5] text-[14px] tracking-[-0.5px] whitespace-nowrap">
                      View All
                    </span>
                  </button>
                </div>

                {/* 4 guidance cards — 2×2 grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-[16px] w-full">
                  {GUIDANCE.map(g => (
                    <div
                      key={g.id}
                      className="bg-[#f8fafc] border border-[#f1f5f9] flex gap-[16px] h-[90px]
                                 items-start p-[17px] rounded-[12px] cursor-pointer
                                 hover:bg-[#f0f5ff] transition-colors"
                    >
                      <div className="bg-white border border-[#e2e8f0] drop-shadow-[0px_1px_1px_rgba(0,0,0,0.05)]
                                      flex items-center justify-center rounded-[8px] shrink-0 size-[48px]">
                        <img src={g.icon} alt="" className="size-[16px] object-contain" />
                      </div>
                      <div className="flex flex-col gap-[4px] overflow-hidden">
                        <div className="flex gap-[8px] items-center">
                          <div className={`${g.tagBg} flex h-[19px] items-center justify-center px-[8px] rounded-[4px] shrink-0`}>
                            <span className={`font-bold ${g.tagText} text-[10px] leading-[15px] whitespace-nowrap`}>
                              {g.tag}
                            </span>
                          </div>
                          <p className="font-bold leading-[20px] text-[#0f172a] text-[14px] tracking-[-0.5px] whitespace-nowrap">
                            {g.title}
                          </p>
                        </div>
                        <p className="font-normal text-[#64748b] text-[12px] tracking-[-0.5px] leading-[16px] truncate">
                          {g.desc}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* RIGHT column — w-[351px] ────────────────────────────────────*/}
            <div className="flex flex-col gap-[32px] w-full xl:w-[351px] xl:shrink-0">

              {/* RECENT ACTIVITY ───────────────────────────────────────────
                  Figma: bg-white, border-[#f1f5f9], drop-shadow, rounded-[24px],
                  gap-[24px], h-[400px], p-[25px]
              ────────────────────────────────────────────────────────────── */}
              <div className="bg-white border border-[#f1f5f9] drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)]
                              flex flex-col gap-[24px] p-[25px] rounded-[24px] w-full">

                <div className="flex items-center justify-between w-full">
                  <p className="font-bold leading-[24px] text-[#0f172a] text-[16px] tracking-[-0.5px] whitespace-nowrap">
                    Recent Activity
                  </p>
                  <button
                    type="button"
                    className="flex items-center justify-center rounded-[8px] size-[32px] hover:bg-[#f8fafc] transition-colors"
                  >
                    <img src={imgMoreDots} alt="more" className="w-[14px] h-[16px] object-contain" />
                  </button>
                </div>

                {/* Timeline */}
                <div className="flex flex-col gap-[24px] w-full">
                  {activity.map((item: ActivityItem, idx: number) => (
                    <div key={item.id} className="flex flex-col gap-[4px] pl-[32px] relative shrink-0">
                      <p className="font-medium leading-[20px] text-[#0f172a] text-[14px] tracking-[-0.5px] whitespace-nowrap">
                        {item.title}
                      </p>
                      <p className="font-normal leading-[16px] text-[#64748b] text-[12px] tracking-[-0.5px] whitespace-nowrap">
                        {item.description}
                      </p>
                      <p className="font-medium leading-[15px] text-[#94a3b8] text-[10px] tracking-[-0.5px] whitespace-nowrap">
                        {formatTs(item.timestamp)}
                      </p>
                      {/* Colored dot */}
                      <div
                        className="absolute h-[8px] left-0 rounded-full top-[4px] w-[8px]"
                        style={{ backgroundColor: item.color }}
                      />
                      {/* Vertical connector line — between items */}
                      {idx < activity.length - 1 && (
                        <div className="absolute bg-[#f1f5f9] h-[65px] left-[3px] top-[16px] w-px" />
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* PROFILE READINESS ─────────────────────────────────────────
                  Figma: bg-white, border-[#f1f5f9], drop-shadow, rounded-[24px],
                  gap-[16px], h-[170px], p-[25px]
              ────────────────────────────────────────────────────────────── */}
              <div className="bg-white border border-[#f1f5f9] drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)]
                              flex flex-col gap-[16px] p-[25px] rounded-[24px] w-full">
                <p className="font-bold leading-[24px] text-[#0f172a] text-[16px] tracking-[-0.5px] whitespace-nowrap">
                  Profile Readiness
                </p>

                <div className="flex gap-[24px] items-center w-full">
                  {/* Donut — size-[85px] */}
                  <div className="relative shrink-0 size-[85px]">
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="font-bold text-[#0f172a] text-[14px] tracking-[-0.5px] whitespace-nowrap">
                        {readiness}%
                      </span>
                    </div>
                    <div className="p-[5px] size-[85px]">
                      <img src={imgDonut} alt="" className="size-[80px] object-contain" />
                    </div>
                  </div>

                  {/* Legend */}
                  <div className="flex flex-col gap-[8px]">
                    <div className="flex gap-[8px] items-center">
                      <img src={imgDotFilled} alt="" className="size-[8px] object-contain shrink-0" />
                      <p className="font-normal leading-[16px] text-[#475569] text-[12px] tracking-[-0.5px] whitespace-nowrap">
                        Personal Info (Done)
                      </p>
                    </div>
                    <div className="flex gap-[8px] items-center">
                      <img src={imgDotFilled} alt="" className="size-[8px] object-contain shrink-0" />
                      <p className="font-normal leading-[16px] text-[#475569] text-[12px] tracking-[-0.5px] whitespace-nowrap">
                        Passport (Done)
                      </p>
                    </div>
                    <div className="flex gap-[8px] items-center">
                      <img src={imgDotEmpty} alt="" className="size-[8px] object-contain shrink-0" />
                      <p className="font-normal leading-[16px] text-[#94a3b8] text-[12px] tracking-[-0.5px] whitespace-nowrap">
                        Education History
                      </p>
                    </div>
                  </div>
                </div>
              </div>

            </div>{/* end RIGHT column */}
          </div>{/* end TWO COLUMN ROW */}
        </div>
      </PageContent>
    </div>
  );
}