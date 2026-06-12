// src/pages/admin/SubscriptionPricing.tsx
//
// Cleaned: inline CheckIcon/XIcon → subscription-pricing/ folder

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPricingStats, fetchPlans, fetchActiveSubscriptions, fetchCoupons,
  createPlan, updatePlan, togglePlan, createCoupon, cancelSubscription, exportSubscriptions,
  type Plan, type Subscription,
} from "../../api/admin/subscriptions.api";

/* ── Icon imports ─────────────────────────────────────────────────── */
import iconCheck from "../../assets/icons/subscription-pricing/feature-check.svg";
import iconX     from "../../assets/icons/subscription-pricing/feature-x.svg";

// ── UI helpers ────────────────────────────────────────────────────
function CheckIcon() { return <img src={iconCheck} alt="" style={{ width: 14, height: 11 }} />; }
function XIcon() { return <img src={iconX} alt="" style={{ width: 12, height: 12 }} />; }
function Spinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 48 }}>
      <div style={{ width: 32, height: 32, borderRadius: "50%", border: "3px solid #e5e7eb", borderTopColor: "#2563eb", animation: "spin 0.8s linear infinite" }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
function EmptyRow({ text }: { text: string }) {
  return <div style={{ padding: "32px 0", textAlign: "center", fontSize: 14, color: "#9ca3af", letterSpacing: "-0.5px" }}>{text}</div>;
}
function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ background: "white", borderRadius: 12, border: "1px solid #f3f4f6", boxShadow: "0 2px 2px rgba(0,0,0,0.06),0 4px 3px rgba(0,0,0,0.1)", overflow: "hidden", ...style }}>{children}</div>;
}
function pct(n: number) { return `${n >= 0 ? "+" : ""}${n}%`; }

const inputStyle: React.CSSProperties = { width: "100%", boxSizing: "border-box", height: 40, border: "1px solid #d1d5db", borderRadius: 8, padding: "0 12px", fontSize: 14, outline: "none" };
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div style={{ marginBottom: 14 }}><label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 }}>{label}</label>{children}</div>;
}
function Modal({ title, onClose, children, width = 560 }: { title: string; onClose: () => void; children: React.ReactNode; width?: number }) {
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "40px 16px", zIndex: 1000, overflowY: "auto" }}>
      <div onClick={e => e.stopPropagation()} style={{ background: "white", borderRadius: 12, width: "100%", maxWidth: width, boxShadow: "0 10px 40px rgba(0,0,0,0.2)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "20px 24px", borderBottom: "1px solid #f3f4f6" }}>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#111827", letterSpacing: "-0.5px" }}>{title}</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 24, cursor: "pointer", color: "#6b7280", lineHeight: 1 }}>×</button>
        </div>
        <div style={{ padding: 24 }}>{children}</div>
      </div>
    </div>
  );
}
function Row({ l, v }: { l: string; v: React.ReactNode }) {
  return <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 0", borderBottom: "1px solid #f9fafb", gap: 16 }}>
    <span style={{ fontSize: 13, color: "#6b7280" }}>{l}</span>
    <span style={{ fontSize: 13, fontWeight: 600, color: "#111827", textAlign: "right" }}>{v}</span>
  </div>;
}

const emptyPlanForm = { name: "", slug: "", description: "", monthly: "", annual: "", trialDays: "0", maxApplications: "", maxDocuments: "", maxMessages: "", isPublic: true, isFeatured: false, highlightColor: "" };
const emptyCouponForm = { code: "", name: "", description: "", discount_type: "percentage", discount_value: "", max_uses: "", valid_until: "", is_active: true };

export default function SubscriptionPricing() {
  const qc = useQueryClient();

  const [modal, setModal] = useState<null | { type: "createPlan" | "planDetails" | "subDetails" | "addCoupon"; data?: any }>(null);
  const [planForm, setPlanForm] = useState(emptyPlanForm);
  const [planMode, setPlanMode] = useState<"create" | "edit">("create");
  const [editId, setEditId] = useState<string | null>(null);
  const [couponForm, setCouponForm] = useState(emptyCouponForm);

  const { data: stats,      isLoading: l1 } = useQuery({ queryKey: ["pricing-stats"], queryFn: fetchPricingStats });
  const { data: plans,      isLoading: l2 } = useQuery({ queryKey: ["plans"],         queryFn: fetchPlans });
  const { data: activeSubs, isLoading: l3 } = useQuery({ queryKey: ["active-subs"],   queryFn: () => fetchActiveSubscriptions() });
  const { data: coupons,    isLoading: l4 } = useQuery({ queryKey: ["coupons"],       queryFn: () => fetchCoupons() });

  const planMut = useMutation({
    mutationFn: (body: Record<string, unknown>) => planMode === "edit" && editId ? updatePlan(editId, body) : createPlan(body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["plans"] }); qc.invalidateQueries({ queryKey: ["pricing-stats"] }); setModal(null); },
  });
  const toggleMut = useMutation({
    mutationFn: (id: string) => togglePlan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plans"] }),
  });
  const couponMut = useMutation({
    mutationFn: (body: Record<string, unknown>) => createCoupon(body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["coupons"] }); setModal(null); },
  });
  const cancelMut = useMutation({
    mutationFn: (id: string) => cancelSubscription(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["active-subs"] }); setModal(null); },
  });

  const handleExport = async () => {
    try {
      const blob = await exportSubscriptions();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "subscriptions.csv"; a.click();
      URL.revokeObjectURL(url);
    } catch { alert("Export failed — check console."); }
  };

  const openCreatePlan = () => { setPlanForm(emptyPlanForm); setPlanMode("create"); setEditId(null); setModal({ type: "createPlan" }); };
  const openEditPlan = (p: Plan) => {
    setPlanForm({ name: p.name, slug: p.slug, description: p.description,
      monthly: String(p.monthlyCents / 100), annual: String(p.annualCents / 100), trialDays: String(p.trialDays),
      maxApplications: p.maxApplications == null ? "" : String(p.maxApplications),
      maxDocuments: p.maxDocuments == null ? "" : String(p.maxDocuments),
      maxMessages: p.maxMessages == null ? "" : String(p.maxMessages),
      isPublic: p.isPublic, isFeatured: p.isFeatured, highlightColor: p.highlightColor ?? "" });
    setPlanMode("edit"); setEditId(p.id); setModal({ type: "createPlan" });
  };
  const submitPlan = () => {
    const f = planForm;
    planMut.mutate({
      name: f.name, slug: f.slug, description: f.description,
      price_monthly_cents: Math.round(Number(f.monthly || 0) * 100),
      price_annual_cents: Math.round(Number(f.annual || 0) * 100),
      currency: "USD", trial_days: Number(f.trialDays || 0),
      max_applications: f.maxApplications === "" ? null : Number(f.maxApplications),
      max_documents: f.maxDocuments === "" ? null : Number(f.maxDocuments),
      max_messages: f.maxMessages === "" ? null : Number(f.maxMessages),
      is_active: true, is_public: f.isPublic, is_featured: f.isFeatured,
      display_order: 0, highlight_color: f.highlightColor || null, features: [],
    });
  };
  const submitCoupon = () => {
    const f = couponForm;
    couponMut.mutate({
      code: f.code, name: f.name || f.code, description: f.description,
      discount_type: f.discount_type, discount_value: Number(f.discount_value || 0),
      valid_from: new Date().toISOString(),
      valid_until: f.valid_until ? new Date(f.valid_until).toISOString() : null,
      max_uses: f.max_uses === "" ? null : Number(f.max_uses),
      is_active: f.is_active,
    });
  };

  const matrixCols = plans ?? [];
  const matrixRows: string[] = [];
  const seen = new Set<string>();
  matrixCols.forEach(p => p.featureRows.forEach(r => { if (!seen.has(r.text)) { seen.add(r.text); matrixRows.push(r.text); } }));

  const subs = activeSubs?.subscriptions ?? [];

  return (
    <main className="p-4 sm:p-8" style={{ fontFamily: "'Inter',sans-serif", minHeight: "100vh", background: "#f9fafb", overflowY: "auto", display: "flex", flexDirection: "column", gap: 32 }}>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-xl sm:text-3xl" style={{ fontWeight: 700, color: "#111827", margin: 0, letterSpacing: "-0.5px" }}>Subscription &amp; Pricing Management</h1>
          <p className="text-sm sm:text-base" style={{ color: "#4b5563", margin: "8px 0 0", letterSpacing: "-0.5px" }}>Manage subscription plans, pricing structures, billing cycles, and customer subscriptions</p>
        </div>
        <div className="flex flex-wrap gap-2 sm:gap-3 sm:flex-shrink-0">
          <button onClick={handleExport} className="text-sm sm:text-base" style={{ height: 42, background: "white", border: "1px solid #d1d5db", borderRadius: 8, padding: "0 14px", cursor: "pointer", fontWeight: 500, color: "#374151" }}>Export Data</button>
          <button onClick={openCreatePlan} className="text-sm sm:text-base" style={{ height: 42, background: "#2563eb", border: "none", borderRadius: 8, padding: "0 14px", cursor: "pointer", fontWeight: 500, color: "white" }}>+ Create New Plan</button>
        </div>
      </div>

      {l1 ? <Spinner /> : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {[
            { label: "Total Subscribers", value: (stats?.totalSubscribers ?? 0).toLocaleString(), sub: `${stats?.activeSubscribers ?? 0} active`, trend: pct(stats?.activeChangePct ?? 0), up: (stats?.activeChangePct ?? 0) >= 0, bg: "#dbeafe" },
            { label: "Monthly Recurring Revenue", value: stats?.mrrDisplay ?? "—", sub: `ARR ${stats?.arrDisplay ?? "—"}`, trend: pct(stats?.mrrChangePct ?? 0), up: (stats?.mrrChangePct ?? 0) >= 0, bg: "#dcfce7" },
            { label: "Churn Rate", value: `${stats?.churnRatePct ?? 0}%`, sub: `${stats?.churnedThisMonth ?? 0} churned this month`, trend: "—", up: false, bg: "#fee2e2" },
            { label: "Trial Subscribers", value: (stats?.trialSubscribers ?? 0).toLocaleString(), sub: `${stats?.pastDueCount ?? 0} past due`, trend: pct(stats?.trialChangePct ?? 0), up: (stats?.trialChangePct ?? 0) >= 0, bg: "#fef9c3" },
          ].map(s => (
            <Card key={s.label}><div style={{ padding: 24 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <div style={{ width: 48, height: 48, borderRadius: 8, background: s.bg, display: "flex", alignItems: "center", justifyContent: "center" }}><span style={{ fontSize: 20 }}>{s.up ? "📈" : "📉"}</span></div>
                <span style={{ fontSize: 14, fontWeight: 600, color: s.up ? "#16a34a" : "#dc2626" }}>{s.trend}</span>
              </div>
              <p style={{ fontSize: 13, fontWeight: 500, color: "#6b7280", margin: "0 0 4px" }}>{s.label}</p>
              <p style={{ fontSize: 28, fontWeight: 700, color: "#111827", margin: "0 0 4px" }}>{s.value}</p>
              <p style={{ fontSize: 12, color: "#6b7280", margin: 0 }}>{s.sub}</p>
            </div></Card>
          ))}
        </div>
      )}

      <Card>
        <div style={{ padding: "32px 32px 0", display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24 }}>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "#111827", margin: 0, letterSpacing: "-0.5px" }}>Subscription Plans</h2>
            <p style={{ fontSize: 16, color: "#4b5563", margin: "4px 0 0" }}>Manage pricing tiers, features, and billing cycles</p>
          </div>
          <button onClick={openCreatePlan} style={{ border: "none", borderRadius: 8, background: "#2563eb", padding: "9px 17px", fontSize: 14, color: "white", cursor: "pointer" }}>+ Add Plan</button>
        </div>
        {l2 ? <Spinner /> : (plans?.length ?? 0) === 0 ? <div style={{ padding: "0 32px 32px" }}><EmptyRow text="No subscription plans found." /></div> : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 px-4 pb-8 sm:px-8">
            {(plans ?? []).map((plan: Plan) => (
              <div key={plan.id} style={{ position: "relative", borderRadius: 12, border: "1px solid #f3f4f6", overflow: "hidden" }}>
                {plan.popular && <div style={{ position: "absolute", top: -10, left: "50%", transform: "translateX(-50%)", background: plan.accentColor, borderRadius: 6, padding: "4px 8px", zIndex: 10 }}><span style={{ fontSize: 11, fontWeight: 700, color: "white", whiteSpace: "nowrap" }}>MOST POPULAR</span></div>}
                <div style={{ background: plan.headerBg, padding: "26px 26px 16px", borderBottom: "1px solid #f3f4f6" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.6px", color: plan.status === "active" ? "#15803d" : "#6b7280", background: plan.status === "active" ? "#dcfce7" : "#f3f4f6", padding: "3.5px 13px", borderRadius: 9999 }}>{plan.status.toUpperCase()}</span>
                    <button onClick={() => toggleMut.mutate(plan.id)} title="Toggle active/inactive" style={{ background: "none", border: "none", cursor: "pointer", fontSize: 13, color: "#6b7280" }}>{toggleMut.isPending ? "…" : "⏻"}</button>
                  </div>
                  <h3 style={{ fontSize: 22, fontWeight: 700, color: "#111827", margin: "0 0 6px" }}>{plan.name}</h3>
                  <p style={{ fontSize: 14, color: "#6b7280", margin: "0 0 12px" }}>{plan.tagline}</p>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                    <span style={{ fontSize: 32, fontWeight: 700, color: plan.accentColor }}>{plan.price === "custom" ? "Custom" : `$${plan.price}`}</span>
                    {plan.price !== "custom" && <span style={{ fontSize: 16, color: "#6b7280" }}>/month</span>}
                  </div>
                  <p style={{ fontSize: 12, color: "#6b7280", margin: "4px 0 0" }}>{plan.priceNote}</p>
                </div>
                <div style={{ padding: "16px 26px", borderBottom: "1px solid #f3f4f6", display: "flex", flexDirection: "column", gap: 8 }}>
                  {[{ l: "Active Subscribers", v: plan.subscribers.toLocaleString() }, { l: "Monthly Revenue", v: plan.revenue == null ? "—" : `$${plan.revenue.toLocaleString()}` }].map(r => (
                    <div key={r.l} style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontSize: 13, color: "#6b7280" }}>{r.l}</span><span style={{ fontSize: 13, fontWeight: 600, color: "#111827" }}>{r.v}</span>
                    </div>
                  ))}
                </div>
                <div style={{ padding: "16px 26px", borderBottom: "1px solid #f3f4f6", display: "flex", flexDirection: "column", gap: 8 }}>
                  {plan.features.slice(0, 5).map((f: string) => (
                    <div key={f} style={{ display: "flex", alignItems: "center", gap: 10 }}><CheckIcon /><span style={{ fontSize: 13, color: "#374151" }}>{f}</span></div>
                  ))}
                  {plan.features.length > 5 && <span style={{ fontSize: 12, color: "#9ca3af" }}>+{plan.features.length - 5} more</span>}
                </div>
                <div style={{ padding: "16px 26px", display: "flex", gap: 8 }}>
                  <button onClick={() => openEditPlan(plan)} style={{ flex: 1, height: 38, border: "1px solid #e5e7eb", borderRadius: 8, background: "white", fontSize: 14, fontWeight: 500, color: "#374151", cursor: "pointer" }}>Edit</button>
                  <button onClick={() => setModal({ type: "planDetails", data: plan })} style={{ flex: 1, height: 38, border: "1px solid #e5e7eb", borderRadius: 8, background: "white", fontSize: 14, fontWeight: 500, color: "#374151", cursor: "pointer" }}>Details</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <div style={{ padding: "32px 32px 0", marginBottom: 24 }}>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: "#111827", margin: 0, letterSpacing: "-0.5px" }}>Feature Management Matrix</h2>
          <p style={{ fontSize: 16, color: "#4b5563", margin: "4px 0 0" }}>Features available in each subscription tier</p>
        </div>
        {l2 ? <Spinner /> : matrixRows.length === 0 ? <div style={{ padding: "0 32px 32px" }}><EmptyRow text="No features configured." /></div> : (
          <div style={{ overflowX: "auto", paddingBottom: 32 }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb" }}>
                <th style={{ padding: "16px 24px", textAlign: "left", fontSize: 14, fontWeight: 600, color: "#374151", whiteSpace: "nowrap" }}>Feature</th>
                {matrixCols.map(p => (<th key={p.id} style={{ padding: "16px 24px", textAlign: "center", fontSize: 14, fontWeight: 600, color: "#374151", whiteSpace: "nowrap" }}>{p.name}</th>))}
              </tr></thead>
              <tbody>
                {matrixRows.map((row, i) => (
                  <tr key={row} style={{ borderBottom: "1px solid #f3f4f6", background: i % 2 === 0 ? "white" : "#fafafa" }}>
                    <td style={{ padding: "14px 24px", fontSize: 14, fontWeight: 600, color: "#111827" }}>{row}</td>
                    {matrixCols.map(p => {
                      const fr = p.featureRows.find(x => x.text === row);
                      return <td key={p.id} style={{ padding: "14px 24px", textAlign: "center" }}><div style={{ display: "flex", justifyContent: "center" }}>{fr?.included ? <CheckIcon /> : <XIcon />}</div></td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card><div style={{ padding: 32, display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: "#111827", margin: 0 }}>Active Subscriptions</h2>
          <button onClick={handleExport} style={{ border: "1px solid #e5e7eb", borderRadius: 8, background: "white", padding: "7px 14px", fontSize: 14, color: "#374151", cursor: "pointer" }}>Export</button>
        </div>
        {l3 ? <Spinner /> : subs.length === 0 ? <EmptyRow text="No active subscriptions." /> : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {subs.map((sub: Subscription) => (
              <div key={sub.id} style={{ borderBottom: "1px solid #f3f4f6", padding: "17px 0" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 9999, background: sub.avatarBg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}><span style={{ fontSize: 14, fontWeight: 600, color: "white" }}>{sub.initials}</span></div>
                    <div><p style={{ fontSize: 15, fontWeight: 600, color: "#111827", margin: "0 0 2px" }}>{sub.customerName}</p><p style={{ fontSize: 12, color: "#6b7280", margin: 0 }}>{sub.customerEmail}</p></div>
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 500, background: sub.planBg, color: sub.planColor, padding: "3.5px 10px", borderRadius: 6 }}>{sub.planName}</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8, marginBottom: 10 }}>
                  {[{ l: "Started", v: sub.started }, { l: "Next Billing", v: sub.nextBilling }, { l: sub.billingCycle, v: sub.price }].map(c => (
                    <div key={c.l}><p style={{ fontSize: 12, color: "#6b7280", margin: "0 0 2px" }}>{c.l}</p><p style={{ fontSize: 14, fontWeight: 600, color: "#111827", margin: 0 }}>{c.v}</p></div>
                  ))}
                </div>
                <button onClick={() => setModal({ type: "subDetails", data: sub })} style={{ fontSize: 13, fontWeight: 500, color: "#2563eb", background: "none", border: "none", cursor: "pointer", padding: 0 }}>View Details →</button>
              </div>
            ))}
          </div>
        )}
        <span style={{ fontSize: 14, color: "#6b7280" }}>Showing {subs.length} of {activeSubs?.total ?? subs.length} subscriptions</span>
      </div></Card>

      <Card>
        <div style={{ padding: "32px 32px 0", display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24 }}>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "#111827", margin: 0, letterSpacing: "-0.5px" }}>Discount Codes &amp; Coupons</h2>
            <p style={{ fontSize: 16, color: "#4b5563", margin: "4px 0 0" }}>Create and manage promotional codes</p>
          </div>
          <button onClick={() => { setCouponForm(emptyCouponForm); setModal({ type: "addCoupon" }); }} style={{ background: "#2563eb", border: "none", borderRadius: 8, padding: "12px 16px", color: "white", fontSize: 16, fontWeight: 500, cursor: "pointer" }}>+ Create Coupon</button>
        </div>
        {l4 ? <Spinner /> : (coupons?.items?.length ?? 0) === 0 ? <div style={{ padding: "0 32px 32px" }}><EmptyRow text="No coupons found." /></div> : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 px-4 pb-8 sm:px-8">
            {(coupons?.items ?? []).map((c: any) => {
              const status = c.is_expired ? "expired" : (c.is_active === false ? "inactive" : "active");
              const sBg = status === "active" ? "#dcfce7" : "#fee2e2", sColor = status === "active" ? "#15803d" : "#b91c1c";
              const disc = c.discount_display || ((c.discount_type === "percentage" || c.discount_type === "percent") ? `${c.discount_value}%` : `$${c.discount_value}`);
              return (
                <div key={c.id ?? c.code} style={{ border: "1px solid #f3f4f6", borderRadius: 10, padding: 26 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, background: sBg, color: sColor, padding: "3.5px 13px", borderRadius: 9999, letterSpacing: "0.6px" }}>{status.toUpperCase()}</span>
                  <h3 style={{ fontSize: 24, fontWeight: 700, color: "#111827", margin: "12px 0 6px" }}>{c.code ?? "—"}</h3>
                  <p style={{ fontSize: 14, color: "#6b7280", margin: "0 0 8px" }}>{c.description || c.name || ""}</p>
                  <p style={{ fontSize: 12, color: "#6b7280", margin: "0 0 4px" }}>📅 Expires: {c.valid_until ? new Date(c.valid_until).toLocaleDateString() : "—"}</p>
                  <p style={{ fontSize: 12, color: "#6b7280", margin: "0 0 12px" }}>🔖 Used: {c.uses_count ?? 0} / {c.max_uses ? c.max_uses : "∞"}</p>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ fontSize: 14, color: "#6b7280" }}>Discount</span><span style={{ fontSize: 14, fontWeight: 600, color: "#111827" }}>{disc}</span></div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* ───────── Modals (unchanged structurally — using CheckIcon component) ───────── */}

      {modal?.type === "createPlan" && (
        <Modal title={planMode === "edit" ? "Edit Plan" : "Create New Plan"} onClose={() => setModal(null)}>
          <Field label="Plan Name"><input style={inputStyle} value={planForm.name} onChange={e => setPlanForm({ ...planForm, name: e.target.value })} /></Field>
          <Field label="Slug (unique, lowercase)"><input style={inputStyle} value={planForm.slug} onChange={e => setPlanForm({ ...planForm, slug: e.target.value })} /></Field>
          <Field label="Description"><input style={inputStyle} value={planForm.description} onChange={e => setPlanForm({ ...planForm, description: e.target.value })} /></Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Monthly Price ($)"><input type="number" style={inputStyle} value={planForm.monthly} onChange={e => setPlanForm({ ...planForm, monthly: e.target.value })} /></Field>
            <Field label="Annual Price ($)"><input type="number" style={inputStyle} value={planForm.annual} onChange={e => setPlanForm({ ...planForm, annual: e.target.value })} /></Field>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Trial Days"><input type="number" style={inputStyle} value={planForm.trialDays} onChange={e => setPlanForm({ ...planForm, trialDays: e.target.value })} /></Field>
            <Field label="Highlight Color (hex)"><input style={inputStyle} placeholder="#5B6CF6" value={planForm.highlightColor} onChange={e => setPlanForm({ ...planForm, highlightColor: e.target.value })} /></Field>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <Field label="Max Applications"><input type="number" style={inputStyle} placeholder="∞" value={planForm.maxApplications} onChange={e => setPlanForm({ ...planForm, maxApplications: e.target.value })} /></Field>
            <Field label="Max Documents"><input type="number" style={inputStyle} placeholder="∞" value={planForm.maxDocuments} onChange={e => setPlanForm({ ...planForm, maxDocuments: e.target.value })} /></Field>
            <Field label="Max Messages"><input type="number" style={inputStyle} placeholder="∞" value={planForm.maxMessages} onChange={e => setPlanForm({ ...planForm, maxMessages: e.target.value })} /></Field>
          </div>
          <div style={{ display: "flex", gap: 20, margin: "4px 0 16px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, color: "#374151", cursor: "pointer" }}><input type="checkbox" checked={planForm.isPublic} onChange={e => setPlanForm({ ...planForm, isPublic: e.target.checked })} />Public</label>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, color: "#374151", cursor: "pointer" }}><input type="checkbox" checked={planForm.isFeatured} onChange={e => setPlanForm({ ...planForm, isFeatured: e.target.checked })} />Featured (Most Popular)</label>
          </div>
          {planMut.isError && <p style={{ color: "#dc2626", fontSize: 13, margin: "0 0 12px" }}>Error: {(planMut.error as any)?.response?.data?.detail ? JSON.stringify((planMut.error as any).response.data.detail) : (planMut.error as Error).message}</p>}
          <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
            <button onClick={() => setModal(null)} style={{ height: 42, padding: "0 18px", border: "1px solid #d1d5db", borderRadius: 8, background: "white", fontSize: 14, fontWeight: 500, color: "#374151", cursor: "pointer" }}>Cancel</button>
            <button onClick={submitPlan} disabled={planMut.isPending || !planForm.name || !planForm.slug} style={{ height: 42, padding: "0 18px", border: "none", borderRadius: 8, background: (planMut.isPending || !planForm.name || !planForm.slug) ? "#9ca3af" : "#2563eb", color: "white", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>{planMut.isPending ? "Saving…" : (planMode === "edit" ? "Save Changes" : "Create Plan")}</button>
          </div>
        </Modal>
      )}

      {modal?.type === "planDetails" && (() => { const p: Plan = modal.data; return (
        <Modal title={`${p.name} — Plan Details`} onClose={() => setModal(null)}>
          <Row l="Status" v={p.status.toUpperCase()} />
          <Row l="Slug" v={p.slug} />
          <Row l="Monthly" v={p.monthlyDisplay} />
          <Row l="Annual" v={p.annualDisplay} />
          <Row l="Trial Days" v={p.trialDays} />
          <Row l="Public" v={p.isPublic ? "Yes" : "No"} />
          <Row l="Featured" v={p.isFeatured ? "Yes" : "No"} />
          <Row l="Max Applications" v={p.maxApplications ?? "Unlimited"} />
          <Row l="Max Documents" v={p.maxDocuments ?? "Unlimited"} />
          <Row l="Max Messages" v={p.maxMessages ?? "Unlimited"} />
          <Row l="Active Subscribers" v={p.subscribers.toLocaleString()} />
          <div style={{ marginTop: 16 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "#374151", margin: "0 0 8px" }}>Included Features</p>
            {p.features.length === 0 ? <span style={{ fontSize: 13, color: "#9ca3af" }}>None</span> : p.features.map(f => (
              <div key={f} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}><CheckIcon /><span style={{ fontSize: 13, color: "#374151" }}>{f}</span></div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 20 }}>
            <button onClick={() => { setModal(null); openEditPlan(p); }} style={{ height: 42, padding: "0 18px", border: "none", borderRadius: 8, background: "#2563eb", color: "white", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>Edit Plan</button>
          </div>
        </Modal>
      ); })()}

      {modal?.type === "subDetails" && (() => { const s: Subscription = modal.data; return (
        <Modal title="Subscription Details" onClose={() => setModal(null)}>
          <Row l="Customer" v={s.customerName} />
          <Row l="Email" v={s.customerEmail} />
          <Row l="Role" v={s.userRole} />
          <Row l="Plan" v={s.planName} />
          <Row l="Status" v={s.status} />
          <Row l="Billing Cycle" v={s.billingCycle} />
          <Row l="Amount" v={s.price} />
          <Row l="Started" v={s.started} />
          <Row l="Next Billing" v={s.nextBilling} />
          <Row l="Trial End" v={s.trialEnd} />
          <Row l="Coupon" v={s.couponCode ?? "—"} />
          <Row l="Discount" v={s.discountDisplay ?? "—"} />
          <Row l="Payment Processor" v={s.paymentProcessor ?? "—"} />
          <Row l="Assigned by Admin" v={s.assignedByAdmin ? "Yes" : "No"} />
          <Row l="Created" v={s.created} />
          {cancelMut.isError && <p style={{ color: "#dc2626", fontSize: 13, margin: "12px 0 0" }}>Error: {(cancelMut.error as Error).message}</p>}
          <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 20 }}>
            <button onClick={() => setModal(null)} style={{ height: 42, padding: "0 18px", border: "1px solid #d1d5db", borderRadius: 8, background: "white", fontSize: 14, fontWeight: 500, color: "#374151", cursor: "pointer" }}>Close</button>
            <button onClick={() => { if (confirm("Cancel this subscription?")) cancelMut.mutate(s.id); }} disabled={cancelMut.isPending} style={{ height: 42, padding: "0 18px", border: "none", borderRadius: 8, background: "#dc2626", color: "white", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>{cancelMut.isPending ? "Cancelling…" : "Cancel Subscription"}</button>
          </div>
        </Modal>
      ); })()}

      {modal?.type === "addCoupon" && (
        <Modal title="Create Coupon" onClose={() => setModal(null)}>
          <Field label="Code"><input style={inputStyle} value={couponForm.code} onChange={e => setCouponForm({ ...couponForm, code: e.target.value.toUpperCase() })} /></Field>
          <Field label="Name"><input style={inputStyle} value={couponForm.name} onChange={e => setCouponForm({ ...couponForm, name: e.target.value })} /></Field>
          <Field label="Description"><input style={inputStyle} value={couponForm.description} onChange={e => setCouponForm({ ...couponForm, description: e.target.value })} /></Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Discount Type"><select style={inputStyle} value={couponForm.discount_type} onChange={e => setCouponForm({ ...couponForm, discount_type: e.target.value })}><option value="percentage">Percentage (%)</option><option value="fixed_amount">Fixed Amount ($)</option></select></Field>
            <Field label="Discount Value"><input type="number" min="0" step="0.01" style={inputStyle} value={couponForm.discount_value} onChange={e => setCouponForm({ ...couponForm, discount_value: e.target.value })} /></Field>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Max Uses"><input type="number" style={inputStyle} placeholder="∞" value={couponForm.max_uses} onChange={e => setCouponForm({ ...couponForm, max_uses: e.target.value })} /></Field>
            <Field label="Valid Until"><input type="date" style={inputStyle} value={couponForm.valid_until} onChange={e => setCouponForm({ ...couponForm, valid_until: e.target.value })} /></Field>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, color: "#374151", cursor: "pointer", margin: "4px 0 16px" }}><input type="checkbox" checked={couponForm.is_active} onChange={e => setCouponForm({ ...couponForm, is_active: e.target.checked })} />Active</label>
          {couponMut.isError && <p style={{ color: "#dc2626", fontSize: 13, margin: "0 0 12px" }}>Error: {(couponMut.error as any)?.response?.data?.detail ? JSON.stringify((couponMut.error as any).response.data.detail) : (couponMut.error as Error).message}</p>}
          {Number(couponForm.discount_value) <= 0 && couponForm.discount_value !== "" && <p style={{ color: "#dc2626", fontSize: 13, margin: "0 0 12px" }}>Discount value must be greater than 0.</p>}
          <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
            <button onClick={() => setModal(null)} style={{ height: 42, padding: "0 18px", border: "1px solid #d1d5db", borderRadius: 8, background: "white", fontSize: 14, fontWeight: 500, color: "#374151", cursor: "pointer" }}>Cancel</button>
            <button onClick={submitCoupon} disabled={couponMut.isPending || !couponForm.code || Number(couponForm.discount_value) <= 0} style={{ height: 42, padding: "0 18px", border: "none", borderRadius: 8, background: (couponMut.isPending || !couponForm.code || Number(couponForm.discount_value) <= 0) ? "#9ca3af" : "#2563eb", color: "white", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>{couponMut.isPending ? "Creating…" : "Create Coupon"}</button>
          </div>
        </Modal>
      )}

    </main>
  );
}
