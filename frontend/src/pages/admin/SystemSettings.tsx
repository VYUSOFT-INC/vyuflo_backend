// src/pages/admin/SystemSettings.tsx
//
// Cleaned: inline SVG icons replaced with common/ imports.
// Save bar is ALWAYS visible — buttons disabled when no edits.

import { useState, useEffect, useMemo } from "react";
import { useLocation } from "react-router-dom";
import { fetchSettings, bulkUpdateSettings } from "../../api/admin/settings.api";
import type { SettingItem } from "../../types/admin/settings.types";

/* ── Icon imports (common only) ─────────────────────────────────────── */
import iconInfo from "../../assets/icons/common/info.svg";
import iconSave from "../../assets/icons/common/save-white.svg";

// ── Section meta: maps URL hash → setting_group + page title ───────
type NavKey =
  | "general" | "security" | "integrations"
  | "notifications" | "features" | "maintenance";

const HASH_TO_KEY: Record<string, NavKey> = {
  "#general":       "general",
  "#security":      "security",
  "#integrations":  "integrations",
  "#notifications": "notifications",
  "#feature-flags": "features",
  "#maintenance":   "maintenance",
};

const KEY_TO_GROUPS: Record<NavKey, string[]> = {
  general:       ["general"],
  security:      ["security"],
  integrations:  ["email", "sms", "integrations"],
  notifications: ["notifications"],
  features:      ["features"],
  maintenance:   ["maintenance"],
};

const SECTION_META: Record<NavKey, { title: string; subtitle: string }> = {
  general:       { title: "General Settings",  subtitle: "Manage core platform configuration, branding, and regional preferences." },
  security:      { title: "Security & Access", subtitle: "Control authentication, sessions, and account protection." },
  integrations:  { title: "Integrations",      subtitle: "Configure email, SMS, and third-party service connections." },
  notifications: { title: "Notifications",     subtitle: "Manage how and when notifications are sent to users." },
  features:      { title: "Feature Flags",     subtitle: "Enable or disable platform features. Changes are immediate." },
  maintenance:   { title: "Maintenance",       subtitle: "Toggle maintenance mode and the banner message shown to users." },
};

// ── Field components ──────────────────────────────────────────────
function TextField({
  setting, value, onChange,
}: { setting: SettingItem; value: string; onChange: (v: string) => void }) {
  const isNumber = setting.value_type === "integer";
  const isUrl = setting.value_type === "url";
  return (
    <div className="flex flex-col gap-[8px]">
      <label className="text-[14px] font-medium leading-[20px]" style={{ color: "#374151" }}>
        {setting.label}
      </label>
      <div className="relative flex">
        {isUrl && (
          <div
            className="flex items-center px-[13px] py-[11px] rounded-l-[8px] text-[14px] text-[#6b7280] shrink-0"
            style={{ background: "#f9fafb", border: "1px solid #d1d5db", borderRight: "none" }}
          >
            https://
          </div>
        )}
        <input
          type={isNumber ? "number" : "text"}
          value={value}
          disabled={setting.is_readonly}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 min-w-0 px-[17px] py-[11px] text-[14px] text-[#111827] outline-none"
          style={{
            background: setting.is_readonly ? "#f9fafb" : "white",
            border: "1px solid #d1d5db",
            borderRadius: isUrl ? "0 8px 8px 0" : "8px",
            cursor: setting.is_readonly ? "not-allowed" : "text",
          }}
        />
      </div>
      {setting.description && (
        <span className="text-[12px] text-[#9ca3af]">{setting.description}</span>
      )}
    </div>
  );
}

function ToggleField({
  setting, value, onChange,
}: { setting: SettingItem; value: string; onChange: (v: string) => void }) {
  const enabled = value === "true";
  return (
    <div className="flex items-center justify-between py-[12px]" style={{ borderBottom: "1px solid #f3f4f6" }}>
      <div className="flex flex-col gap-[2px] mr-4">
        <span className="text-[14px] font-medium text-[#111827]">{setting.label}</span>
        {setting.description && <span className="text-[12px] text-[#6b7280]">{setting.description}</span>}
      </div>
      <button
        onClick={() => !setting.is_readonly && onChange(enabled ? "false" : "true")}
        style={{
          width: 44, height: 24, borderRadius: 12, border: "none",
          background: enabled ? "#4F46E5" : "#D1D5DB",
          position: "relative", flexShrink: 0,
          cursor: setting.is_readonly ? "not-allowed" : "pointer",
          opacity: setting.is_readonly ? 0.6 : 1,
          transition: "background 0.2s",
        }}
      >
        <span style={{
          position: "absolute", top: 3, left: enabled ? 23 : 3,
          width: 18, height: 18, borderRadius: "50%", background: "#fff",
          transition: "left 0.2s", boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
        }}/>
      </button>
    </div>
  );
}

function SettingsCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      className="bg-white rounded-[14px] overflow-hidden"
      style={{ border: "1px solid rgba(229,231,235,0.6)", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)" }}
    >
      <div className="px-[24px] py-[18px]" style={{ background: "rgba(249,250,251,0.5)", borderBottom: "1px solid #f3f4f6" }}>
        <span className="text-[16px] font-semibold text-[#111827]">{title}</span>
      </div>
      <div className="p-[24px] flex flex-col gap-[20px]">{children}</div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────
export default function SystemSettings() {
  const [settings, setSettings] = useState<SettingItem[]>([]);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [activeNav, setActiveNav] = useState<NavKey>("general");

  const location = useLocation();
  useEffect(() => {
    const key = HASH_TO_KEY[location.hash];
    if (key) setActiveNav(key);
  }, [location.hash]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchSettings();
        if (!cancelled) setSettings(res.items ?? []);
      } catch (e) {
        if (!cancelled) setError((e as Error)?.message || "Could not load settings.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const valueOf = (s: SettingItem) => edits[s.key] !== undefined ? edits[s.key] : s.value;
  const setValue = (key: string, val: string) => setEdits((prev) => ({ ...prev, [key]: val }));

  const visible = useMemo(() => {
    const groups = KEY_TO_GROUPS[activeNav];
    return settings.filter((s) => groups.includes(s.setting_group)).sort((a, b) => a.display_order - b.display_order);
  }, [settings, activeNav]);

  const toggles = visible.filter((s) => s.value_type === "boolean");
  const fields  = visible.filter((s) => s.value_type !== "boolean");

  const hasChanges = Object.keys(edits).length > 0;
  const disabled = saving || !hasChanges;

  const handleDiscard = () => setEdits({});

  const handleSave = async () => {
    const updates = Object.entries(edits).map(([key, value]) => ({ key, value }));
    if (updates.length === 0) return;
    setSaving(true);
    try {
      await bulkUpdateSettings({ updates });
      setSettings((prev) => prev.map((s) => (edits[s.key] !== undefined ? { ...s, value: edits[s.key] } : s)));
      setEdits({});
    } catch {
      alert("Could not save changes. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const meta = SECTION_META[activeNav];

  return (
    <div className="flex flex-col min-h-screen bg-[#f9fafb]" style={{ fontFamily: "'Inter', sans-serif" }}>
      <main className="flex-1 min-w-0 overflow-y-auto" style={{ background: "#f9fafb" }}>
        <div className="flex flex-col gap-6 max-w-[896px] mx-auto p-4 pb-[120px] sm:gap-7 sm:p-6 sm:pb-[120px] lg:p-8 lg:pb-[120px]">

          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-bold leading-7 sm:text-[24px] sm:leading-[32px]" style={{ color: "#111827", letterSpacing: "-0.6px" }}>
              {meta.title}
            </h1>
            <p className="text-[14px] text-[#6b7280] leading-[20px]">{meta.subtitle}</p>
          </div>

          {loading && <div className="text-[14px] text-[#9ca3af] py-10 text-center">Loading settings…</div>}

          {error && !loading && (
            <div className="rounded-[8px] px-[14px] py-[10px] text-[13px]"
              style={{ background: "#FEF3C7", border: "1px solid #FCD34D", color: "#92400E" }}>
              ⚠️ {error}
            </div>
          )}

          {!loading && !error && visible.length === 0 && (
            <div className="rounded-[12px] px-[24px] py-[40px] text-center text-[14px] text-[#9ca3af] bg-white"
              style={{ border: "1px solid rgba(229,231,235,0.6)" }}>
              No settings in this section yet.
            </div>
          )}

          {!loading && fields.length > 0 && (
            <SettingsCard title="Configuration">
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 sm:gap-6">
                {fields.map((s) => (
                  <TextField key={s.key} setting={s} value={valueOf(s)} onChange={(v) => setValue(s.key, v)} />
                ))}
              </div>
            </SettingsCard>
          )}

          {!loading && toggles.length > 0 && (
            <SettingsCard title="Options">
              <div className="flex flex-col">
                {toggles.map((s) => (
                  <ToggleField key={s.key} setting={s} value={valueOf(s)} onChange={(v) => setValue(s.key, v)} />
                ))}
              </div>
            </SettingsCard>
          )}

        </div>
      </main>

      {/* ── Save bar — ALWAYS visible. Buttons disabled when no edits. ── */}
      <div className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-center px-4 py-3 sm:px-8 sm:py-4"
        style={{
          background: "rgba(255,255,255,0.85)", backdropFilter: "blur(6px)",
          borderTop: "1px solid rgba(229,231,235,0.8)", boxShadow: "0 -4px 6px -1px rgba(0,0,0,0.05)",
        }}>
        <div className="max-w-[896px] w-full flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-[12px]">
            <img src={iconInfo} alt="" className="h-[14px] w-[14px]" style={{ opacity: hasChanges ? 1 : 0.5 }} />
            <span className="text-[14px]" style={{ color: hasChanges ? "#4b5563" : "#9ca3af" }}>
              {hasChanges
                ? `${Object.keys(edits).length} unsaved change(s).`
                : "Edit any field to enable saving."}
            </span>
          </div>
          <div className="flex items-center gap-[12px]">
            <button
              onClick={handleDiscard}
              disabled={disabled}
              className="px-[21px] py-[11px] rounded-[8px] bg-white text-[14px] font-medium text-[#374151] hover:bg-gray-50"
              style={{
                border: "1px solid #d1d5db",
                cursor: disabled ? "not-allowed" : "pointer",
                opacity: disabled ? 0.5 : 1,
              }}>
              Discard
            </button>
            <button
              onClick={handleSave}
              disabled={disabled}
              className="flex items-center gap-[8px] px-[20px] py-[10px] rounded-[8px] text-white text-[14px] font-medium"
              style={{
                backgroundImage: "linear-gradient(135deg,#2563eb 0%,#9333ea 100%)",
                border: "none",
                cursor: disabled ? "not-allowed" : "pointer",
                opacity: disabled ? 0.55 : 1,
              }}>
              <img src={iconSave} alt="" className="h-[12px] w-[11px]" />
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
