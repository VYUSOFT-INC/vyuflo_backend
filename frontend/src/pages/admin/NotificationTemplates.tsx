// src/pages/admin/NotificationTemplates.tsx
//
// Cleaned: inline SVG icons → common/ + notification-templates/ folders

import { useState, useEffect, useMemo } from "react";
import { fetchTemplates, toggleTemplate, deleteTemplate, createTemplate } from "../../api/admin/notificationTemplates.api";
import type { NotificationTemplate, CreateTemplatePayload } from "../../types/admin/notificationTemplates.types";

/* ── Icon imports ─────────────────────────────────────────────────── */
// Common
import iconSearch     from "../../assets/icons/common/search.svg";
import iconPlus       from "../../assets/icons/common/plus-white.svg";
import iconPencil     from "../../assets/icons/common/pencil-edit.svg";
import iconCopy       from "../../assets/icons/common/copy.svg";
import iconTrash      from "../../assets/icons/common/trash-red.svg";

// Page-specific channel icons (4 channel colors)
import iconChannelEmail from "../../assets/icons/notification-templates/channel-email.svg";
import iconChannelInapp from "../../assets/icons/notification-templates/channel-inapp.svg";
import iconChannelSms   from "../../assets/icons/notification-templates/channel-sms.svg";
import iconChannelPush  from "../../assets/icons/notification-templates/channel-push.svg";

// ── Channel normalisation + config ────────────────────────────────
type ChannelKey = "email" | "in_app" | "sms" | "push" | "other";

function channelKey(raw: string): ChannelKey {
  const c = (raw || "").toLowerCase().replace(/[\s-]/g, "_");
  if (c === "email") return "email";
  if (c === "in_app" || c === "inapp") return "in_app";
  if (c === "sms") return "sms";
  if (c === "push") return "push";
  return "other";
}

const CHANNEL_CONFIG: Record<ChannelKey, { label: string; bg: string; color: string; icon: string }> = {
  email:  { label: "Email",  bg: "#dbeafe", color: "#1d4ed8", icon: iconChannelEmail },
  in_app: { label: "In-App", bg: "#f3e8ff", color: "#7e22ce", icon: iconChannelInapp },
  sms:    { label: "SMS",    bg: "#dcfce7", color: "#15803d", icon: iconChannelSms   },
  push:   { label: "Push",   bg: "#fef3c7", color: "#92400e", icon: iconChannelPush  },
  other:  { label: "Other",  bg: "#f3f4f6", color: "#4b5563", icon: iconChannelEmail },
};

const ICON_BG: Record<ChannelKey, string> = {
  email: "#eff6ff", in_app: "#faf5ff", sms: "#f0fdf4", push: "#fffbeb", other: "#f9fafb",
};

function ChannelBadge({ raw }: { raw: string }) {
  const ck = channelKey(raw);
  const cfg = CHANNEL_CONFIG[ck];
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: cfg.bg, borderRadius: 6, padding: "4px 10px" }}>
      <img src={cfg.icon} alt="" style={{ width: 10, height: 10 }} />
      <span style={{ fontSize: 12, fontWeight: 500, color: cfg.color, lineHeight: "16px", whiteSpace: "nowrap" }}>{cfg.label}</span>
    </div>
  );
}

function TemplateIconBox({ raw }: { raw: string }) {
  const ck = channelKey(raw);
  return (
    <div style={{ width: 32, height: 32, borderRadius: 4, flexShrink: 0, background: ICON_BG[ck], display: "flex", alignItems: "center", justifyContent: "center" }}>
      <img src={CHANNEL_CONFIG[ck].icon} alt="" style={{ width: 10, height: 10 }} />
    </div>
  );
}

function ToggleSwitch({ on, disabled, onChange }: { on: boolean; disabled?: boolean; onChange: () => void }) {
  return (
    <button
      onClick={() => !disabled && onChange()}
      style={{
        position: "relative", width: 48, height: 24, borderRadius: 9999,
        background: on ? "#3b82f6" : "#d1d5db", border: "none",
        cursor: disabled ? "not-allowed" : "pointer", flexShrink: 0,
        transition: "background 0.2s", opacity: disabled ? 0.6 : 1,
      }}
    >
      <div style={{
        position: "absolute", top: 0, left: on ? "auto" : 0, right: on ? 0 : "auto",
        width: 24, height: 24, borderRadius: 9999, background: "white",
        border: `4px solid ${on ? "#3b82f6" : "#e5e7eb"}`, transition: "all 0.2s", boxSizing: "border-box",
      }}/>
    </button>
  );
}

function formatDate(iso: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return iso;
  }
}

const CHANNEL_OPTIONS = [
  { value: "email",  label: "Email"  },
  { value: "in_app", label: "In-App" },
  { value: "sms",    label: "SMS"    },
  { value: "push",   label: "Push"   },
];

const CATEGORY_OPTIONS = [
  { value: "case_update", label: "Case Update" },
  { value: "deadline",    label: "Deadline"    },
  { value: "news",        label: "News"        },
  { value: "security",    label: "Security"    },
  { value: "billing",     label: "Billing"     },
];

function CreateTemplateModal({
  onClose, onCreated,
}: { onClose: () => void; onCreated: (t: NotificationTemplate) => void }) {
  const [form, setForm] = useState<CreateTemplatePayload>({
    name: "", event_key: "", description: "", channel: "email",
    subject: "", body_text: "", body_html: "", category: "case_update",
    available_placeholders: "", is_active: true,
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const set = (k: keyof CreateTemplatePayload) => (v: string | boolean) =>
    setForm((p) => ({ ...p, [k]: v }));

  const isEmail = form.channel === "email";
  const canSave = form.name.trim() && form.event_key.trim() && (form.body_text || "").trim() && form.category && !saving;

  const handleCreate = async () => {
    if (!canSave) return;
    setErr(null);
    let placeholders = (form.available_placeholders || "").trim();
    if (placeholders === "") {
      placeholders = "[]";
    } else {
      try {
        JSON.parse(placeholders);
      } catch {
        setErr('Available Placeholders must be valid JSON, e.g. ["{{user_name}}","{{due_date}}"]');
        return;
      }
    }

    setSaving(true);
    try {
      const payload: CreateTemplatePayload = {
        ...form,
        body_html: form.body_html || form.body_text || "",
        available_placeholders: placeholders,
      };
      const created = await createTemplate(payload);
      onCreated(created);
      onClose();
    } catch {
      setErr("Could not create template. Check required fields and try again.");
    } finally {
      setSaving(false);
    }
  };

  const labelStyle: React.CSSProperties = { display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 };
  const inputStyle: React.CSSProperties = { width: "100%", padding: "10px 12px", border: "1.5px solid #d1d5db", borderRadius: 8, fontSize: 14, color: "#111827", outline: "none", boxSizing: "border-box", fontFamily: "inherit" };

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, backdropFilter: "blur(2px)", padding: 20 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: "#fff", borderRadius: 14, width: 560, maxHeight: "90vh", overflowY: "auto", boxShadow: "0 12px 48px rgba(0,0,0,0.18)" }}>
        <div style={{ padding: "24px 28px 16px", borderBottom: "1px solid #f3f4f6" }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: "#111827", margin: 0 }}>Create Template</h2>
          <p style={{ fontSize: 13.5, color: "#6b7280", margin: "6px 0 0" }}>Define a new notification template and its trigger.</p>
        </div>

        <div style={{ padding: "20px 28px", display: "flex", flexDirection: "column", gap: 16 }}>
          {err && <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", color: "#B91C1C", borderRadius: 8, padding: "8px 12px", fontSize: 13 }}>{err}</div>}

          <div>
            <label style={labelStyle}>Template Name *</label>
            <input style={inputStyle} placeholder="e.g. Visa Application Approved" value={form.name} onChange={(e) => set("name")(e.target.value)} />
          </div>
          <div>
            <label style={labelStyle}>Description</label>
            <input style={inputStyle} placeholder="Short description shown in the list" value={form.description} onChange={(e) => set("description")(e.target.value)} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={labelStyle}>Channel *</label>
              <select style={inputStyle} value={form.channel} onChange={(e) => set("channel")(e.target.value)}>
                {CHANNEL_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Trigger Event *</label>
              <input style={inputStyle} placeholder="e.g. Status_Changed_Approved" value={form.event_key} onChange={(e) => set("event_key")(e.target.value)} />
            </div>
          </div>

          {isEmail && (
            <div>
              <label style={labelStyle}>Subject</label>
              <input style={inputStyle} placeholder="Email subject line" value={form.subject} onChange={(e) => set("subject")(e.target.value)} />
            </div>
          )}

          <div>
            <label style={labelStyle}>Body *</label>
            <textarea style={{ ...inputStyle, minHeight: 96, resize: "vertical" }} placeholder={'Message content. Use placeholders like {{user_name}}, {{due_date}}.'} value={form.body_text} onChange={(e) => set("body_text")(e.target.value)} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={labelStyle}>Category *</label>
              <select style={inputStyle} value={form.category} onChange={(e) => set("category")(e.target.value)}>
                {CATEGORY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Available Placeholders</label>
              <input style={inputStyle} placeholder={'["{{user_name}}","{{due_date}}"]'} value={form.available_placeholders} onChange={(e) => set("available_placeholders")(e.target.value)} />
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 4 }}>
            <span style={{ fontSize: 14, fontWeight: 500, color: "#111827" }}>Active</span>
            <ToggleSwitch on={form.is_active} onChange={() => set("is_active")(!form.is_active)} />
          </div>
        </div>

        <div style={{ position: "sticky", bottom: 0, background: "#fff", padding: "16px 28px 24px", display: "flex", justifyContent: "flex-end", gap: 10, borderTop: "1px solid #f3f4f6" }}>
          <button onClick={onClose} style={{ padding: "9px 20px", border: "1.5px solid #d1d5db", borderRadius: 8, background: "#fff", fontSize: 14, fontWeight: 500, color: "#374151", cursor: "pointer" }}>Cancel</button>
          <button
            onClick={handleCreate}
            disabled={!canSave}
            style={{
              padding: "9px 22px", border: "none", borderRadius: 8,
              background: canSave ? "linear-gradient(135deg,#2563eb 0%,#9333ea 100%)" : "#A5B4FC",
              fontSize: 14, fontWeight: 600, color: "#fff",
              cursor: canSave ? "pointer" : "not-allowed",
            }}
          >
            {saving ? "Creating…" : "Create Template"}
          </button>
        </div>
      </div>
    </div>
  );
}

const PAGE_SIZE = 10;

export default function NotificationTemplates() {
  const [templates, setTemplates] = useState<NotificationTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [channelFilter, setChannelFilter] = useState("All Channels");
  const [statusFilter, setStatusFilter] = useState("All Statuses");
  const [currentPage, setCurrentPage] = useState(1);
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchTemplates({ page: 1, limit: 100 });
        if (!cancelled) setTemplates(res.items ?? []);
      } catch (e) {
        if (!cancelled) setError((e as Error)?.message || "Could not load templates.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleToggle = async (tmpl: NotificationTemplate) => {
    const next = !tmpl.is_active;
    setTemplates((prev) => prev.map((t) => (t.id === tmpl.id ? { ...t, is_active: next } : t)));
    try {
      await toggleTemplate(tmpl.id, { is_active: next });
    } catch {
      setTemplates((prev) => prev.map((t) => (t.id === tmpl.id ? { ...t, is_active: !next } : t)));
      alert("Could not update status. Please try again.");
    }
  };

  const handleDelete = async (tmpl: NotificationTemplate) => {
    if (!window.confirm(`Delete "${tmpl.name}"? This cannot be undone.`)) return;
    const prev = templates;
    setTemplates((p) => p.filter((t) => t.id !== tmpl.id));
    try {
      await deleteTemplate(tmpl.id);
    } catch {
      setTemplates(prev);
      alert("Could not delete template.");
    }
  };

  const filtered = useMemo(() => {
    return templates.filter((t) => {
      const q = search.toLowerCase();
      const matchSearch = !q || t.name.toLowerCase().includes(q) || (t.event_key || "").toLowerCase().includes(q);
      const matchChannel = channelFilter === "All Channels" || CHANNEL_CONFIG[channelKey(t.channel)].label === channelFilter;
      const matchStatus = statusFilter === "All Statuses" || (statusFilter === "Active" ? t.is_active : !t.is_active);
      return matchSearch && matchChannel && matchStatus;
    });
  }, [templates, search, channelFilter, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const page = Math.min(currentPage, totalPages);
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div style={{ minHeight: "100vh", background: "#f9fafb", fontFamily: "'Inter', sans-serif" }}>
      <main className="p-4 sm:p-8" style={{ maxWidth: 1440, width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", gap: 24 }}>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <h1 className="text-xl sm:text-2xl" style={{ fontWeight: 700, color: "#111827", margin: 0 }}>Notification Templates</h1>
            <p className="text-xs sm:text-sm" style={{ color: "#6b7280", margin: 0 }}>Manage automated emails, in-app alerts, and SMS notifications.</p>
          </div>
          <button onClick={() => setShowCreate(true)} className="self-start sm:self-auto" style={{
            display: "flex", alignItems: "center", gap: 8,
            backgroundImage: "linear-gradient(135deg,#2563eb 0%,#9333ea 100%)",
            border: "none", borderRadius: 8, padding: "10px 20px", cursor: "pointer",
            boxShadow: "0 1px 1px rgba(0,0,0,0.05)",
          }}>
            <img src={iconPlus} alt="" style={{ width: 12, height: 12 }} />
            <span style={{ fontSize: 14, fontWeight: 500, color: "white", whiteSpace: "nowrap" }}>Create Template</span>
          </button>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between" style={{
          background: "white", border: "1px solid #f3f4f6", borderRadius: 12, padding: 16,
          boxShadow: "0 1px 1px rgba(0,0,0,0.05)",
        }}>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4 w-full sm:w-auto">
            <div className="relative w-full sm:w-64">
              <input
                value={search}
                onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
                placeholder="Search template name..."
                style={{
                  width: "100%", boxSizing: "border-box", background: "white",
                  border: "1px solid #e5e7eb", borderRadius: 8, padding: "10px 17px 11px 37px",
                  fontSize: 14, color: "#111827", outline: "none",
                }}
              />
              <div style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)" }}>
                <img src={iconSearch} alt="" style={{ width: 14, height: 14 }} />
              </div>
            </div>

            <div className="flex gap-2">
              <select value={channelFilter} onChange={(e) => { setChannelFilter(e.target.value); setCurrentPage(1); }}
                className="flex-1 sm:flex-none"
                style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: "9px 12px", fontSize: 14, color: "#374151", cursor: "pointer", outline: "none" }}>
                {["All Channels", "Email", "In-App", "SMS", "Push"].map((o) => <option key={o}>{o}</option>)}
              </select>

              <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
                className="flex-1 sm:flex-none"
                style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 8, padding: "9px 12px", fontSize: 14, color: "#374151", cursor: "pointer", outline: "none" }}>
                {["All Statuses", "Active", "Inactive"].map((o) => <option key={o}>{o}</option>)}
              </select>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 14, fontWeight: 500, color: "#111827" }}>{filtered.length}</span>
            <span style={{ fontSize: 14, color: "#6b7280" }}>templates found</span>
          </div>
        </div>

        <div style={{ background: "white", border: "1px solid #f3f4f6", borderRadius: 12, overflow: "hidden", boxShadow: "0 1px 2px rgba(0,0,0,0.05)" }}>

          {loading && <div style={{ padding: 48, textAlign: "center", fontSize: 14, color: "#9ca3af" }}>Loading templates…</div>}

          {error && !loading && (
            <div style={{ margin: 16, padding: "10px 14px", borderRadius: 8, background: "#FEF3C7", border: "1px solid #FCD34D", color: "#92400E", fontSize: 13 }}>
              ⚠️ {error}
            </div>
          )}

          {!loading && !error && filtered.length === 0 && (
            <div style={{ padding: 48, textAlign: "center", fontSize: 14, color: "#9ca3af" }}>No templates found.</div>
          )}

          {!loading && !error && filtered.length > 0 && (
            <div style={{ overflowX: "auto", WebkitOverflowScrolling: "touch" }}>
            <table style={{ width: "100%", minWidth: 900, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                  {[
                    { label: "TEMPLATE NAME", align: "left" as const },
                    { label: "CHANNEL", align: "left" as const },
                    { label: "TRIGGER EVENT", align: "left" as const },
                    { label: "LAST MODIFIED", align: "left" as const },
                    { label: "STATUS", align: "left" as const },
                    { label: "ACTIONS", align: "right" as const },
                  ].map((col) => (
                    <th key={col.label} style={{ padding: "16px 24px", textAlign: col.align, fontSize: 12, fontWeight: 700, color: "#6b7280", letterSpacing: "0.6px", textTransform: "uppercase" }}>
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {paginated.map((tmpl, idx) => (
                  <tr
                    key={tmpl.id}
                    onMouseEnter={() => setHoveredRow(tmpl.id)}
                    onMouseLeave={() => setHoveredRow(null)}
                    style={{
                      borderTop: idx === 0 ? "none" : "1px solid #f3f4f6",
                      background: hoveredRow === tmpl.id ? "#fafafa" : "white",
                      transition: "background 0.15s",
                    }}
                  >
                    <td style={{ padding: "16px 24px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <TemplateIconBox raw={tmpl.channel} />
                        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                          <span style={{ fontSize: 14, fontWeight: 500, color: "#111827", lineHeight: "20px" }}>{tmpl.name}</span>
                          <span style={{ fontSize: 12, color: "#6b7280", lineHeight: "16px" }}>{tmpl.description || ""}</span>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: "16px 24px" }}><ChannelBadge raw={tmpl.channel} /></td>
                    <td style={{ padding: "16px 24px" }}>
                      <span style={{ fontSize: 14, color: "#4b5563", whiteSpace: "nowrap" }}>{tmpl.event_key}</span>
                    </td>
                    <td style={{ padding: "16px 24px" }}>
                      <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontSize: 14, color: "#6b7280", lineHeight: "20px" }}>{formatDate(tmpl.updated_at)}</span>
                        {tmpl.last_modified_by_name && (
                          <span style={{ fontSize: 12, color: "#6b7280", lineHeight: "16px" }}>by {tmpl.last_modified_by_name}</span>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: "16px 24px" }}>
                      <ToggleSwitch on={tmpl.is_active} onChange={() => handleToggle(tmpl)} />
                    </td>
                    <td style={{ padding: "16px 24px", textAlign: "right" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8, opacity: hoveredRow === tmpl.id ? 1 : 0, transition: "opacity 0.15s" }}>
                        <button title="Edit" style={{ padding: 6, borderRadius: 4, border: "none", background: "transparent", cursor: "pointer" }}>
                          <img src={iconPencil} alt="" style={{ width: 14, height: 14 }} />
                        </button>
                        <button title="Duplicate" style={{ padding: 6, borderRadius: 4, border: "none", background: "transparent", cursor: "pointer" }}>
                          <img src={iconCopy} alt="" style={{ width: 14, height: 14 }} />
                        </button>
                        <button title="Delete" onClick={() => handleDelete(tmpl)} style={{ padding: 6, borderRadius: 4, border: "none", background: "transparent", cursor: "pointer" }}>
                          <img src={iconTrash} alt="" style={{ width: 12, height: 13 }} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}

          {!loading && !error && filtered.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "17px 24px 16px", borderTop: "1px solid #f3f4f6", flexWrap: "wrap", gap: 12 }}>
              <span style={{ fontSize: 14, color: "#6b7280" }}>
                Showing <strong style={{ color: "#111827" }}>{(page - 1) * PAGE_SIZE + 1}</strong> to{" "}
                <strong style={{ color: "#111827" }}>{Math.min(page * PAGE_SIZE, filtered.length)}</strong> of{" "}
                <strong style={{ color: "#111827" }}>{filtered.length}</strong> results
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <button onClick={() => setCurrentPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: "7px 13px", fontSize: 14, color: "#6b7280", background: "white", cursor: page === 1 ? "default" : "pointer", opacity: page === 1 ? 0.5 : 1 }}>
                  Previous
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).slice(0, 5).map((p) => (
                  <button key={p} onClick={() => setCurrentPage(p)}
                    style={{
                      border: page === p ? "1px solid #2563eb" : "1px solid #e5e7eb",
                      borderRadius: 6, padding: "7px 13px", fontSize: 14,
                      fontWeight: page === p ? 500 : 400,
                      color: page === p ? "#2563eb" : "#6b7280",
                      background: page === p ? "#eff6ff" : "white", cursor: "pointer",
                    }}>
                    {p}
                  </button>
                ))}
                <button onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                  style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: "7px 13px", fontSize: 14, color: "#4b5563", background: "white", cursor: page >= totalPages ? "default" : "pointer", opacity: page >= totalPages ? 0.5 : 1 }}>
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {showCreate && (
        <CreateTemplateModal
          onClose={() => setShowCreate(false)}
          onCreated={(t) => setTemplates((prev) => [t, ...prev])}
        />
      )}
    </div>
  );
}
