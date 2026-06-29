// src/pages/admin/VisaTypesManager.tsx
//
// Cleaned: inline SVGs → common/ + visa-types-manager/ folders
// Exception: VisaCardIcon stays inline (takes dynamic color prop)

import { useState, useEffect, useMemo } from "react";
import { fetchVisaTypes, createVisaType, fetchVisaTypeDetail } from "../../api/admin/visa-types.api";
import type { VisaTypeItem, VisaTypeStats, CreateVisaTypePayload } from "../../types/admin/visaTypes.types";

/* ── Icon imports ─────────────────────────────────────────────────── */
// Common
import iconDownload     from "../../assets/icons/common/download.svg";
import iconPlus         from "../../assets/icons/common/plus-white.svg";
import iconXClose       from "../../assets/icons/common/x-close.svg";
import iconSearch       from "../../assets/icons/common/search.svg";
import iconChevronDown  from "../../assets/icons/common/chevron-down.svg";
import iconDots         from "../../assets/icons/common/dots-vertical.svg";
import iconEye          from "../../assets/icons/common/eye-view.svg";
import iconPencil       from "../../assets/icons/common/pencil-edit.svg";

// Page-specific KPI stat icons
import iconStatTotal    from "../../assets/icons/visa-types-manager/stat-total.svg";
import iconStatActive   from "../../assets/icons/visa-types-manager/stat-active.svg";
import iconStatPending  from "../../assets/icons/visa-types-manager/stat-pending.svg";
import iconStatCases    from "../../assets/icons/visa-types-manager/stat-cases.svg";

// VisaCardIcon kept inline because each card uses a dynamic accent color
const VisaCardIcon = ({ color }: { color: string }) => (
  <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
    <rect x="1" y="4" width="20" height="14" rx="3" stroke={color} strokeWidth="1.6"/>
    <path d="M1 8H21" stroke={color} strokeWidth="1.6"/>
    <path d="M5 13H9M5 15.5H7.5" stroke={color} strokeWidth="1.4" strokeLinecap="round"/>
    <rect x="14" y="12" width="5" height="3.5" rx="1" fill={color} fillOpacity="0.3" stroke={color} strokeWidth="1.2"/>
  </svg>
);

// ── Category mapping ──────────────────────────────────────────────
const CATEGORY_LABELS: Record<string, string> = {
  employment: "Work Visa", student: "Student Visa", visitor: "Visitor Visa",
  permanent_resident: "Immigrant Visa", exchange: "Exchange Visa",
};
const CATEGORY_ORDER = ["employment", "student", "visitor", "permanent_resident", "exchange"];

const CATEGORY_OPTIONS = [
  { label: "All Categories", value: "" },
  { label: "Work Visa", value: "employment" },
  { label: "Student Visa", value: "student" },
  { label: "Visitor Visa", value: "visitor" },
  { label: "Immigrant Visa", value: "permanent_resident" },
  { label: "Exchange Visa", value: "exchange" },
];
const CATEGORY_FORM_OPTIONS = CATEGORY_OPTIONS.filter((o) => o.value);
const STATUS_OPTIONS = [
  { label: "All Statuses", value: "" },
  { label: "Active", value: "active" },
  { label: "Inactive", value: "inactive" },
  { label: "Pending Review", value: "pending_review" },
];
const STATUS_FORM_OPTIONS = STATUS_OPTIONS.filter((o) => o.value);
const SORT_OPTIONS = [
  { label: "Name (A-Z)", sort_by: "name", sort_order: "asc" as const },
  { label: "Name (Z-A)", sort_by: "name", sort_order: "desc" as const },
  { label: "Most Cases", sort_by: "display_order", sort_order: "asc" as const },
  { label: "Recently Modified", sort_by: "updated_at", sort_order: "desc" as const },
];

const ACCENTS = [
  { color: "#2563eb", bg: "#dbeafe" }, { color: "#9333ea", bg: "#f3e8ff" },
  { color: "#16a34a", bg: "#dcfce7" }, { color: "#ca8a04", bg: "#fef9c3" },
  { color: "#e11d48", bg: "#ffe4e6" }, { color: "#0284c7", bg: "#e0f2fe" },
];

type StatusKey = "active" | "inactive" | "pending_review";
function statusBadge(status: string) {
  const s = (status || "").toLowerCase() as StatusKey;
  const cfg: Record<string, { bg: string; color: string; label: string }> = {
    active: { bg: "#dcfce7", color: "#15803d", label: "Active" },
    inactive: { bg: "#f3f4f6", color: "#4b5563", label: "Inactive" },
    pending_review: { bg: "#fef9c3", color: "#854d0e", label: "Pending" },
  };
  return cfg[s] || { bg: "#f3f4f6", color: "#4b5563", label: status || "—" };
}
function successColor(rate: number) {
  if (rate >= 85) return "#16a34a";
  if (rate >= 70) return "#ca8a04";
  return "#dc2626";
}
function timeAgo(iso: string) {
  if (!iso) return "";
  const d = new Date(iso).getTime();
  const days = Math.floor((Date.now() - d) / 86400000);
  if (days <= 0) return "Modified today";
  if (days === 1) return "Modified 1 day ago";
  if (days < 7) return `Modified ${days} days ago`;
  const weeks = Math.floor(days / 7);
  if (weeks === 1) return "Modified 1 week ago";
  if (weeks < 5) return `Modified ${weeks} weeks ago`;
  return `Modified on ${new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;
}

function VisaTypeCard({ card, accent, onView }: { card: VisaTypeItem; accent: { color: string; bg: string }; onView: (id: string) => void }) {
  const badge = statusBadge(card.status);
  return (
    <div className="bg-white rounded-[12px] flex flex-col"
      style={{ borderLeft: `4px solid ${accent.color}`, boxShadow: "0 2px 2px rgba(0,0,0,0.06), 0 4px 3px rgba(0,0,0,0.1)", padding: "24px 24px 24px 28px", gap: 16 }}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-[16px]">
          <div className="rounded-[8px] flex items-center justify-center shrink-0" style={{ background: accent.bg, width: 48, height: 48 }}>
            <VisaCardIcon color={accent.color} />
          </div>
          <div className="flex flex-col gap-[8px]">
            <p className="font-bold text-[#111827]" style={{ fontSize: 18, lineHeight: "28px", letterSpacing: "-0.5px" }}>{card.name}</p>
            <p className="font-normal text-[#4b5563]" style={{ fontSize: 14, lineHeight: "20px", letterSpacing: "-0.5px" }}>{card.description || ""}</p>
            <div className="flex items-center gap-[12px] flex-wrap">
              <span className="inline-flex items-center justify-center rounded-full px-[8px]" style={{ background: badge.bg, height: 24, fontSize: 12, fontWeight: 500, color: badge.color, lineHeight: "16px", whiteSpace: "nowrap" }}>{badge.label}</span>
              <span className="text-[#6b7280] whitespace-nowrap" style={{ fontSize: 12, lineHeight: "16px" }}>Code: {card.code}</span>
              <span className="text-[#6b7280] whitespace-nowrap" style={{ fontSize: 12, lineHeight: "16px" }}>{card.active_cases_count.toLocaleString()} active cases</span>
            </div>
          </div>
        </div>
        <button style={{ background: "none", border: "none", cursor: "pointer", padding: "2px 6px" }}>
          <img src={iconDots} alt="" style={{ width: 4, height: 14 }} />
        </button>
      </div>

      <div className="flex items-start gap-[16px] pt-[17px]" style={{ borderTop: "1px solid #f3f4f6" }}>
        {[
          { label: "Required Docs", value: `${card.required_documents_count} documents`, color: "#111827" },
          { label: "Processing Time", value: card.processing_time_label || `${card.typical_processing_days} days`, color: "#111827" },
          { label: "Success Rate", value: `${card.success_rate}%`, color: successColor(card.success_rate) },
        ].map((s) => (
          <div key={s.label} className="flex flex-col gap-[4px]" style={{ width: 155 }}>
            <span className="text-[#6b7280] whitespace-nowrap" style={{ fontSize: 12, lineHeight: "16px" }}>{s.label}</span>
            <span className="font-semibold whitespace-nowrap" style={{ fontSize: 14, lineHeight: "20px", color: s.color }}>{s.value}</span>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between pt-[17px]" style={{ borderTop: "1px solid #f3f4f6" }}>
        <div className="flex items-center gap-[8px]">
          <button onClick={() => onView(card.id)} className="flex items-center gap-[4px]" style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}>
            <img src={iconEye} alt="" style={{ width: 16, height: 14 }} />
            <span className="font-medium text-[#2563eb]" style={{ fontSize: 14 }}>View Details</span>
          </button>
          <button className="flex items-center gap-[4px] ml-[8px]" style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}>
            <img src={iconPencil} alt="" style={{ width: 14, height: 14 }} />
            <span className="font-medium text-[#2563eb]" style={{ fontSize: 14 }}>Edit</span>
          </button>
        </div>
        <span className="text-[#6b7280] whitespace-nowrap" style={{ fontSize: 12, lineHeight: "16px" }}>{timeAgo(card.updated_at)}</span>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = { border: "1px solid #d1d5db", borderRadius: 8, padding: "8px 12px", fontSize: 14, color: "#111827", background: "white", width: "100%", height: 40, boxSizing: "border-box", outline: "none" };
const labelStyle: React.CSSProperties = { fontSize: 13, fontWeight: 500, color: "#374151", marginBottom: 4, display: "block" };

function CreateVisaModal({ onClose, onCreated }: { onClose: () => void; onCreated: (v: VisaTypeItem) => void }) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [shortLabel, setShortLabel] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("employment");
  const [status, setStatus] = useState("active");
  const [requiresSponsor, setRequiresSponsor] = useState(false);
  const [requiredDocs, setRequiredDocs] = useState("");
  const [processingDays, setProcessingDays] = useState("");
  const [govFee, setGovFee] = useState("");
  const [uscisUrl, setUscisUrl] = useState("");
  const [displayOrder, setDisplayOrder] = useState("");
  const [successRate, setSuccessRate] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    setErr(null);
    if (!code.trim() || !name.trim() || !category) {
      setErr("Code, Name and Category are required.");
      return;
    }
    const docsArr = requiredDocs.split(/[\n,]/).map((d) => d.trim()).filter(Boolean);

    const payload: CreateVisaTypePayload = {
      code: code.trim(),
      name: name.trim(),
      short_label: shortLabel.trim() || undefined,
      description: description.trim() || undefined,
      category,
      requires_employer_sponsor: requiresSponsor,
      required_documents: JSON.stringify(docsArr),
      typical_processing_days: Number(processingDays) || 0,
      government_fee_usd: Number(govFee) || 0,
      uscis_url: uscisUrl.trim() || undefined,
      display_order: Number(displayOrder) || 0,
      is_active: status === "active",
      status,
      success_rate: Number(successRate) || 0,
    };

    try {
      setSaving(true);
      const created = await createVisaType(payload);
      onCreated(created);
      onClose();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail.map((d: any) => d.msg).join(", ") : (detail || e?.message || "Could not create visa type.");
      setErr(typeof msg === "string" ? msg : "Could not create visa type.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: "white", borderRadius: 12, width: "100%", maxWidth: 640, maxHeight: "90vh", display: "flex", flexDirection: "column", boxShadow: "0 20px 40px rgba(0,0,0,0.2)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 24px", borderBottom: "1px solid #e5e7eb" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#111827" }}>Add New Visa Type</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}>
            <img src={iconXClose} alt="" style={{ width: 20, height: 20 }} />
          </button>
        </div>

        <div style={{ padding: 24, overflowY: "auto", display: "flex", flexDirection: "column", gap: 16 }}>
          {err && <div style={{ background: "#FEF2F2", border: "1px solid #FECACA", color: "#B91C1C", borderRadius: 8, padding: "8px 12px", fontSize: 13 }}>{err}</div>}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={labelStyle}>Code <span style={{ color: "#dc2626" }}>*</span></label>
              <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. H-2A" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Name <span style={{ color: "#dc2626" }}>*</span></label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. H-2A Temporary Agricultural" style={inputStyle} />
            </div>
          </div>

          <div>
            <label style={labelStyle}>Short Label</label>
            <input value={shortLabel} onChange={(e) => setShortLabel(e.target.value)} placeholder="e.g. H-2A" style={inputStyle} />
          </div>

          <div>
            <label style={labelStyle}>Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Short description of this visa type" style={{ ...inputStyle, height: 70, paddingTop: 8, resize: "vertical" }} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={labelStyle}>Category <span style={{ color: "#dc2626" }}>*</span></label>
              <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ ...inputStyle, cursor: "pointer" }}>
                {CATEGORY_FORM_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Status <span style={{ color: "#dc2626" }}>*</span></label>
              <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ ...inputStyle, cursor: "pointer" }}>
                {STATUS_FORM_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label style={labelStyle}>Required Documents</label>
            <textarea value={requiredDocs} onChange={(e) => setRequiredDocs(e.target.value)} placeholder="One per line or comma-separated: Passport Copy, Offer Letter" style={{ ...inputStyle, height: 70, paddingTop: 8, resize: "vertical" }} />
            <span style={{ fontSize: 11, color: "#9ca3af" }}>Separate with commas or new lines.</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
            <div>
              <label style={labelStyle}>Processing Days</label>
              <input type="number" value={processingDays} onChange={(e) => setProcessingDays(e.target.value)} placeholder="0" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Govt Fee (USD)</label>
              <input type="number" value={govFee} onChange={(e) => setGovFee(e.target.value)} placeholder="0" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Success Rate (%)</label>
              <input type="number" value={successRate} onChange={(e) => setSuccessRate(e.target.value)} placeholder="0" style={inputStyle} />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={labelStyle}>USCIS URL</label>
              <input value={uscisUrl} onChange={(e) => setUscisUrl(e.target.value)} placeholder="https://..." style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Display Order</label>
              <input type="number" value={displayOrder} onChange={(e) => setDisplayOrder(e.target.value)} placeholder="0" style={inputStyle} />
            </div>
          </div>

          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 14, color: "#374151" }}>
            <input type="checkbox" checked={requiresSponsor} onChange={(e) => setRequiresSponsor(e.target.checked)} style={{ width: 16, height: 16, cursor: "pointer" }} />
            Requires employer sponsor
          </label>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, padding: "16px 24px", borderTop: "1px solid #e5e7eb" }}>
          <button onClick={onClose} disabled={saving} style={{ padding: "9px 20px", borderRadius: 8, border: "1px solid #d1d5db", background: "white", color: "#374151", fontSize: 14, fontWeight: 500, cursor: "pointer" }}>Cancel</button>
          <button onClick={submit} disabled={saving} style={{ padding: "9px 24px", borderRadius: 8, border: "none", background: "#2563eb", color: "white", fontSize: 14, fontWeight: 500, cursor: saving ? "default" : "pointer", opacity: saving ? 0.7 : 1 }}>
            {saving ? "Creating…" : "Create Visa Type"}
          </button>
        </div>
      </div>
    </div>
  );
}

function exportCSV(items: VisaTypeItem[]) {
  const headers = ["Code", "Name", "Category", "Status", "Description", "Required Docs", "Processing Days", "Govt Fee USD", "Success Rate", "Active Cases", "USCIS URL", "Updated At"];
  const esc = (v: any) => {
    const s = v == null ? "" : String(v);
    return `"${s.replace(/"/g, '""')}"`;
  };
  const rows = items.map((it) => [
    it.code, it.name, CATEGORY_LABELS[it.category] || it.category, it.status,
    it.description || "", it.required_documents_count, it.typical_processing_days,
    it.government_fee_usd, it.success_rate, it.active_cases_count, it.uscis_url || "", it.updated_at,
  ].map(esc).join(","));
  const csv = [headers.map(esc).join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `visa-types-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function DetailModal({ id, onClose }: { id: string; onClose: () => void }) {
  const [data, setData] = useState<VisaTypeItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    fetchVisaTypeDetail(id)
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setErr((e as Error)?.message || "Could not load details."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id]);

  const badge = data ? statusBadge(data.status) : null;

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: "white", borderRadius: 12, width: "100%", maxWidth: 600, maxHeight: "90vh", display: "flex", flexDirection: "column", boxShadow: "0 20px 40px rgba(0,0,0,0.2)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 24px", borderBottom: "1px solid #e5e7eb" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#111827" }}>
            {data ? data.name : "Visa Type Details"}
          </h2>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}>
            <img src={iconXClose} alt="" style={{ width: 20, height: 20 }} />
          </button>
        </div>

        <div style={{ padding: 24, overflowY: "auto", display: "flex", flexDirection: "column", gap: 20 }}>
          {loading && <div style={{ color: "#9ca3af", fontSize: 14, textAlign: "center", padding: "24px 0" }}>Loading details…</div>}
          {err && <div style={{ background: "#FEF2F2", border: "1px solid #FECACA", color: "#B91C1C", borderRadius: 8, padding: "8px 12px", fontSize: 13 }}>{err}</div>}

          {data && (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                {badge && <span style={{ background: badge.bg, color: badge.color, borderRadius: 999, padding: "4px 10px", fontSize: 12, fontWeight: 500 }}>{badge.label}</span>}
                <span style={{ fontSize: 13, color: "#6b7280" }}>Code: <b style={{ color: "#111827" }}>{data.code}</b></span>
                <span style={{ fontSize: 13, color: "#6b7280" }}>{CATEGORY_LABELS[data.category] || data.category}</span>
              </div>

              {data.description && <p style={{ fontSize: 14, color: "#4b5563", lineHeight: "20px" }}>{data.description}</p>}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, padding: "16px 0", borderTop: "1px solid #f3f4f6", borderBottom: "1px solid #f3f4f6" }}>
                {[
                  { label: "Required Docs", value: `${data.required_documents_count} documents` },
                  { label: "Processing Time", value: data.processing_time_label || `${data.typical_processing_days} days` },
                  { label: "Success Rate", value: `${data.success_rate}%`, color: successColor(data.success_rate) },
                  { label: "Active Cases", value: data.active_cases_count.toLocaleString() },
                  { label: "Govt Fee", value: `$${data.government_fee_usd.toLocaleString()}` },
                  { label: "Employer Sponsor", value: data.requires_employer_sponsor ? "Required" : "Not required" },
                ].map((s) => (
                  <div key={s.label} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <span style={{ fontSize: 12, color: "#6b7280" }}>{s.label}</span>
                    <span style={{ fontSize: 14, fontWeight: 600, color: (s as any).color || "#111827" }}>{s.value}</span>
                  </div>
                ))}
              </div>

              <div>
                <h3 style={{ fontSize: 14, fontWeight: 600, color: "#111827", marginBottom: 10 }}>Required Documents</h3>
                {data.required_documents && data.required_documents.length > 0 ? (
                  <ul style={{ display: "flex", flexDirection: "column", gap: 8, listStyle: "none", padding: 0, margin: 0 }}>
                    {data.required_documents.map((doc, i) => (
                      <li key={i} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14, color: "#374151", background: "#f9fafb", border: "1px solid #f3f4f6", borderRadius: 8, padding: "10px 12px" }}>
                        <span style={{ width: 22, height: 22, borderRadius: 6, background: "#eff6ff", color: "#2563eb", fontSize: 12, fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{i + 1}</span>
                        {doc}
                      </li>
                    ))}
                  </ul>
                ) : <p style={{ fontSize: 13, color: "#9ca3af" }}>No required documents listed.</p>}
              </div>

              {data.uscis_url && (
                <div>
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: "#111827", marginBottom: 6 }}>USCIS Reference</h3>
                  <a href={data.uscis_url} target="_blank" rel="noreferrer" style={{ fontSize: 14, color: "#2563eb", wordBreak: "break-all" }}>{data.uscis_url}</a>
                </div>
              )}

              <div style={{ fontSize: 12, color: "#9ca3af", paddingTop: 8, borderTop: "1px solid #f3f4f6" }}>
                {timeAgo(data.updated_at)}{data.modified_by_name ? ` · by ${data.modified_by_name}` : ""}
              </div>
            </>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", padding: "16px 24px", borderTop: "1px solid #e5e7eb" }}>
          <button onClick={onClose} style={{ padding: "9px 20px", borderRadius: 8, border: "1px solid #d1d5db", background: "white", color: "#374151", fontSize: 14, fontWeight: 500, cursor: "pointer" }}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default function VisaTypesManager() {
  const [stats, setStats] = useState<VisaTypeStats | null>(null);
  const [items, setItems] = useState<VisaTypeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [sortIdx, setSortIdx] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const loadData = () => {
    setLoading(true);
    setError(null);
    fetchVisaTypes({ sort_by: "display_order", sort_order: "asc", page: 1, page_size: 100 })
      .then((res) => { setStats(res.stats); setItems(res.items ?? []); })
      .catch((e) => setError((e as Error)?.message || "Could not load visa types."))
      .finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, []);

  const visibleItems = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();
    let list = items.filter((it) => {
      const matchCategory = !category || it.category === category;
      const matchStatus = !status || (it.status || "").toLowerCase() === status;
      const matchSearch = !q || (it.name || "").toLowerCase().includes(q) || (it.code || "").toLowerCase().includes(q);
      return matchCategory && matchStatus && matchSearch;
    });
    const sort = SORT_OPTIONS[sortIdx];
    list = [...list].sort((a, b) => {
      let cmp = 0;
      if (sort.sort_by === "name") cmp = (a.name || "").localeCompare(b.name || "");
      else if (sort.sort_by === "updated_at") cmp = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
      else cmp = (a.display_order ?? 0) - (b.display_order ?? 0);
      return sort.sort_order === "desc" ? -cmp : cmp;
    });
    return list;
  }, [items, category, status, debouncedSearch, sortIdx]);

  const grouped = useMemo(() => {
    const g: Record<string, VisaTypeItem[]> = {};
    visibleItems.forEach((it) => { const k = it.category || "other"; if (!g[k]) g[k] = []; g[k].push(it); });
    return g;
  }, [visibleItems]);

  const orderedCategories = useMemo(() => {
    return Object.keys(grouped).sort((a, b) => {
      const ia = CATEGORY_ORDER.indexOf(a); const ib = CATEGORY_ORDER.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });
  }, [grouped]);

  const STAT_CARDS = stats ? [
    { value: stats.total_visa_types, label: "Total Visa Types", pct: stats.total_pct_change, iconBg: "#dbeafe", icon: iconStatTotal },
    { value: stats.active_visa_types, label: "Active Visa Types", pct: stats.active_pct_change, iconBg: "#dcfce7", icon: iconStatActive },
    { value: stats.pending_review, label: "Pending Review", pct: stats.pending_pct_change, iconBg: "#ffedd5", icon: iconStatPending },
    { value: stats.active_cases, label: "Active Cases", pct: stats.cases_pct_change, iconBg: "#f3e8ff", icon: iconStatCases },
  ] : [];

  const clearAll = () => { setSearch(""); setCategory(""); setStatus(""); setSortIdx(0); };

  return (
    <div className="min-h-screen bg-[#f9fafb]" style={{ fontFamily: "'Inter', sans-serif" }}>
      <main className="overflow-y-auto" style={{ background: "#f9fafb" }}>

        <div className="bg-white flex flex-col gap-3 px-4 sm:flex-row sm:items-center sm:justify-between sm:px-8" style={{ borderBottom: "1px solid #e5e7eb", paddingTop: 20, paddingBottom: 20 }}>
          <div className="flex flex-col gap-[4px]">
            <h1 className="text-xl sm:text-3xl font-bold text-[#111827] tracking-[-0.5px]" style={{ lineHeight: 1.2 }}>Visa Types Manager</h1>
            <p className="text-xs sm:text-base font-normal text-[#4b5563] tracking-[-0.5px]" style={{ lineHeight: "20px" }}>Manage all visa types, requirements, and configurations in the system</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 sm:flex-shrink-0">
            <button onClick={() => exportCSV(visibleItems)} className="flex items-center gap-2 bg-white rounded-lg text-sm sm:text-base" style={{ border: "1px solid #d1d5db", padding: "9px 14px", cursor: "pointer", height: 40 }}>
              <img src={iconDownload} alt="" style={{ width: 16, height: 16 }} />
              <span className="font-medium text-[#374151]">Export All</span>
            </button>
            <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-[#2563eb] rounded-lg text-white text-sm sm:text-base" style={{ border: "none", padding: "8px 14px", cursor: "pointer", height: 40 }}>
              <img src={iconPlus} alt="" style={{ width: 14, height: 16 }} />
              <span className="font-medium whitespace-nowrap">Add New</span>
            </button>
          </div>
        </div>

        <div className="px-4 sm:px-8 py-6 flex flex-col gap-6">

          {error && (
            <div style={{ background: "#FEF3C7", border: "1px solid #FCD34D", color: "#92400E", borderRadius: 8, padding: "10px 14px", fontSize: 13 }}>⚠️ {error}</div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            {loading && !stats
              ? Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="bg-white rounded-[12px] p-[24px]" style={{ boxShadow: "0 2px 2px rgba(0,0,0,0.06), 0 4px 3px rgba(0,0,0,0.1)", height: 152 }}>
                    <div style={{ color: "#9ca3af", fontSize: 13 }}>Loading…</div>
                  </div>
                ))
              : STAT_CARDS.map((stat) => {
                  const pct = stat.pct ?? 0;
                  const pctColor = pct > 0 ? "#16a34a" : pct < 0 ? "#dc2626" : "#ea580c";
                  const arrow = pct > 0 ? "↑" : pct < 0 ? "↓" : "—";
                  return (
                    <div key={stat.label} className="bg-white rounded-[12px] flex flex-col gap-[16px] p-[24px]" style={{ boxShadow: "0 2px 2px rgba(0,0,0,0.06), 0 4px 3px rgba(0,0,0,0.1)" }}>
                      <div className="flex items-center justify-between">
                        <div className="rounded-[8px] flex items-center justify-center" style={{ width: 48, height: 48, background: stat.iconBg }}>
                          <img src={stat.icon} alt="" style={{ width: 20, height: 20 }} />
                        </div>
                        <span className="font-semibold" style={{ fontSize: 14, color: pctColor }}>{arrow} {Math.abs(pct)}%</span>
                      </div>
                      <p className="font-bold text-[#111827]" style={{ fontSize: 24, lineHeight: "32px" }}>{stat.value.toLocaleString()}</p>
                      <p className="font-normal text-[#4b5563]" style={{ fontSize: 14, lineHeight: "20px" }}>{stat.label}</p>
                    </div>
                  );
                })}
          </div>

          <div className="bg-white rounded-[12px] p-[24px] flex flex-col gap-[16px]" style={{ boxShadow: "0 2px 2px rgba(0,0,0,0.06), 0 4px 3px rgba(0,0,0,0.1)" }}>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-[#111827]" style={{ fontSize: 18, lineHeight: "28px" }}>Filters &amp; Search</span>
              <button onClick={clearAll} className="font-medium text-[#2563eb]" style={{ fontSize: 14, background: "none", border: "none", cursor: "pointer" }}>Clear All</button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex flex-col gap-[8px]">
                <label className="font-medium text-[#374151]" style={{ fontSize: 14 }}>Search Visa Types</label>
                <div className="relative">
                  <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name or code..."
                    className="w-full rounded-[8px] outline-none" style={{ border: "1px solid #d1d5db", padding: "8px 16px 8px 40px", fontSize: 16, color: "#111827", background: "white", height: 42, boxSizing: "border-box" }} />
                  <div className="absolute top-[13px] left-[12px] pointer-events-none">
                    <img src={iconSearch} alt="" style={{ width: 16, height: 16 }} />
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-[8px]">
                <label className="font-medium text-[#374151]" style={{ fontSize: 14 }}>Category</label>
                <div className="relative">
                  <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full rounded-[8px] appearance-none outline-none" style={{ border: "1px solid #d1d5db", padding: "8px 40px 8px 16px", fontSize: 16, color: "#111827", background: "white", height: 42, cursor: "pointer", boxSizing: "border-box" }}>
                    {CATEGORY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                  <div className="absolute top-[14px] right-[10px] pointer-events-none">
                    <img src={iconChevronDown} alt="" style={{ width: 16, height: 16 }} />
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-[8px]">
                <label className="font-medium text-[#374151]" style={{ fontSize: 14 }}>Status</label>
                <div className="relative">
                  <select value={status} onChange={(e) => setStatus(e.target.value)} className="w-full rounded-[8px] appearance-none outline-none" style={{ border: "1px solid #d1d5db", padding: "8px 40px 8px 16px", fontSize: 16, color: "#111827", background: "white", height: 42, cursor: "pointer", boxSizing: "border-box" }}>
                    {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                  <div className="absolute top-[14px] right-[10px] pointer-events-none">
                    <img src={iconChevronDown} alt="" style={{ width: 16, height: 16 }} />
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-[8px]">
                <label className="font-medium text-[#374151]" style={{ fontSize: 14 }}>Sort By</label>
                <div className="relative">
                  <select value={sortIdx} onChange={(e) => setSortIdx(Number(e.target.value))} className="w-full rounded-[8px] appearance-none outline-none" style={{ border: "1px solid #d1d5db", padding: "8px 40px 8px 16px", fontSize: 16, color: "#111827", background: "white", height: 42, cursor: "pointer", boxSizing: "border-box" }}>
                    {SORT_OPTIONS.map((o, i) => <option key={o.label} value={i}>{o.label}</option>)}
                  </select>
                  <div className="absolute top-[14px] right-[10px] pointer-events-none">
                    <img src={iconChevronDown} alt="" style={{ width: 16, height: 16 }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {loading && (
            <div className="bg-white rounded-[12px] flex items-center justify-center py-[48px]" style={{ boxShadow: "0 2px 2px rgba(0,0,0,0.06)" }}>
              <span style={{ color: "#9ca3af", fontSize: 14 }}>Loading visa types…</span>
            </div>
          )}

          {!loading && orderedCategories.map((cat) => {
            const cards = grouped[cat];
            return (
              <div key={cat} className="flex flex-col gap-[16px]">
                <div className="flex items-center justify-between">
                  <h2 className="font-bold text-[#111827]" style={{ fontSize: 20, lineHeight: "28px" }}>{CATEGORY_LABELS[cat] || cat}</h2>
                  <button onClick={() => setShowCreate(true)} className="font-medium text-[#2563eb]" style={{ fontSize: 14, background: "none", border: "none", cursor: "pointer" }}>+ Add New</button>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                  {cards.map((card, i) => (
                    <VisaTypeCard key={card.id} card={card} accent={ACCENTS[i % ACCENTS.length]} onView={setDetailId} />
                  ))}
                </div>
              </div>
            );
          })}

          {!loading && !error && visibleItems.length === 0 && (
            <div className="bg-white rounded-[12px] flex flex-col items-center justify-center py-[64px]" style={{ boxShadow: "0 2px 2px rgba(0,0,0,0.06), 0 4px 3px rgba(0,0,0,0.1)" }}>
              <p className="font-semibold text-[#111827]" style={{ fontSize: 18 }}>No visa types found</p>
              <p className="font-normal text-[#6b7280] mt-[8px]" style={{ fontSize: 14 }}>Try adjusting your filters or search terms.</p>
            </div>
          )}

        </div>
      </main>

      {detailId && <DetailModal id={detailId} onClose={() => setDetailId(null)} />}

      {showCreate && (
        <CreateVisaModal
          onClose={() => setShowCreate(false)}
          onCreated={(created) => {
            setItems((prev) => [created, ...prev]);
            loadData();
          }}
        />
      )}
    </div>
  );
}
