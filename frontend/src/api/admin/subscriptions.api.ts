// src/api/subscriptions.api.ts
//
// VisaFlow — Subscription & Pricing API layer.
// All endpoints confirmed via Swagger (Admin — Subscriptions section, 2026-06-05).
// axios baseURL = "/api/v1", so paths below OMIT "/v1". GETs: no trailing slash.

import api from "../axios";

/* ───────────── Raw backend shapes ───────────── */

interface RawPlanFeature {
  id: string; plan_id: string; feature_text: string;
  is_included: boolean; sort_order: number; is_highlighted: boolean;
}
interface RawPlan {
  id: string; name: string; slug: string; description: string;
  price_monthly_cents: number; price_annual_cents: number;
  price_monthly_display: string; price_annual_display: string; price_annual_monthly_equiv: string;
  currency: string; trial_days: number;
  max_applications: number | null; max_documents: number | null; max_messages: number | null;
  is_active: boolean; is_public: boolean; is_featured: boolean;
  display_order: number; highlight_color: string | null;
  active_subscribers: number; trial_subscribers: number; total_subscribers: number;
  features: RawPlanFeature[]; created_at: string; updated_at: string;
}
interface RawSubscription {
  subscription_id: string; user_id: string; user_name: string; user_email: string; user_role: string;
  plan_name: string; plan_slug: string; status: string; billing_cycle: string;
  current_period_start: string; current_period_end: string; trial_end: string | null;
  cancel_at_period_end: boolean; amount_display: string; coupon_code: string | null;
  discount_display: string | null; payment_processor: string | null;
  stripe_subscription_id: string | null; assigned_by_admin: boolean; created_at: string;
}
interface RawStats {
  mrr_cents: number; mrr_display: string; arr_cents: number; arr_display: string;
  mrr_change_pct: number; active_subscribers: number; active_change_pct: number;
  trial_subscribers: number; trial_change_pct: number; churned_this_month: number;
  churn_rate_pct: number; total_subscribers: number; past_due_count: number; paused_count: number;
}

/* ───────────── View-model shapes (page consumes) ───────────── */

export interface PricingStats {
  totalSubscribers: number;
  mrrDisplay: string; mrrChangePct: number; arrDisplay: string;
  activeSubscribers: number; activeChangePct: number;
  trialSubscribers: number; trialChangePct: number;
  churnedThisMonth: number; churnRatePct: number;
  pastDueCount: number; pausedCount: number;
}

export interface Plan {
  id: string; name: string; slug: string;
  popular: boolean; accentColor: string; headerBg: string;
  status: string;                 // "active" | "inactive"
  tagline: string;
  price: number | "custom"; priceNote: string;
  subscribers: number; revenue: number | null;
  features: string[];                              // included only (card)
  featureRows: { text: string; included: boolean }[]; // all (matrix)
  // extra (details modal / edit form)
  description: string; monthlyDisplay: string; annualDisplay: string;
  monthlyCents: number; annualCents: number; trialDays: number;
  maxApplications: number | null; maxDocuments: number | null; maxMessages: number | null;
  isPublic: boolean; isActive: boolean; isFeatured: boolean; highlightColor: string | null;
}

export interface Subscription {
  id: string; initials: string; avatarBg: string;
  customerName: string; customerEmail: string; userRole: string;
  planName: string; planBg: string; planColor: string;
  status: string; started: string; nextBilling: string; trialEnd: string;
  billingCycle: string; price: string;
  couponCode: string | null; discountDisplay: string | null;
  paymentProcessor: string | null; assignedByAdmin: boolean; created: string;
}
export interface ActiveSubscriptionsResponse { subscriptions: Subscription[]; total: number; }

export interface PricingConfig {
  individualBasePrice: number | null; employerBasePrice: number | null;
  lawyerBasePrice: number | null; enterpriseBasePrice: number | null;
  annualDiscount: number | null; trialDays: number | null;
}

/* ───────────── Helpers ───────────── */

const AVATARS = ["#2563eb", "#7c3aed", "#db2777", "#059669", "#d97706", "#0891b2"];
function hash(s: string) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); }
function colorOf(s: string) { return AVATARS[hash(s) % AVATARS.length]; }
function initialsOf(n: string) {
  const p = (n || "").trim().split(/\s+/).filter(Boolean);
  if (!p.length) return "?";
  return (p.length === 1 ? p[0].slice(0, 2) : p[0][0] + p[p.length - 1][0]).toUpperCase();
}
function planBadge(slug: string) {
  switch ((slug || "").toLowerCase()) {
    case "free": return { bg: "#f3f4f6", color: "#6b7280" };
    case "starter": return { bg: "#dbeafe", color: "#1d4ed8" };
    case "professional": return { bg: "#e0e7ff", color: "#4f46e5" };
    case "enterprise": return { bg: "#f3e8ff", color: "#7c3aed" };
    default: return { bg: "#dbeafe", color: "#1d4ed8" };
  }
}
function fmtDate(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "—" : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
function cap(s: string) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ""; }

/* ───────────── Transforms ───────────── */

function planToVM(p: RawPlan): Plan {
  const isCustom = p.price_monthly_cents === 0 && !p.is_public;
  const monthly = p.price_monthly_cents / 100;

  // backend returns duplicate feature rows — dedupe by text
  const seen = new Set<string>();
  const rows: { text: string; included: boolean; sort: number }[] = [];
  [...(p.features ?? [])].sort((a, b) => a.sort_order - b.sort_order).forEach((f) => {
    if (seen.has(f.feature_text)) return;
    seen.add(f.feature_text);
    rows.push({ text: f.feature_text, included: f.is_included, sort: f.sort_order });
  });

  let priceNote = "";
  if (isCustom) priceNote = "Contact sales for pricing";
  else if (p.price_monthly_cents === 0) priceNote = "Free forever";
  else if (p.price_annual_monthly_equiv) priceNote = `or ${p.price_annual_monthly_equiv}/mo billed annually`;

  return {
    id: p.id, name: p.name, slug: p.slug,
    popular: p.is_featured, accentColor: p.highlight_color ?? "#2563eb",
    headerBg: p.is_featured ? "#eef2ff" : "#eff6ff",
    status: p.is_active ? "active" : "inactive",
    tagline: p.description,
    price: isCustom ? "custom" : monthly, priceNote,
    subscribers: p.active_subscribers, revenue: isCustom ? null : Math.round(p.active_subscribers * monthly),
    features: rows.filter((r) => r.included).map((r) => r.text),
    featureRows: rows.map((r) => ({ text: r.text, included: r.included })),
    description: p.description, monthlyDisplay: p.price_monthly_display, annualDisplay: p.price_annual_display,
    monthlyCents: p.price_monthly_cents, annualCents: p.price_annual_cents, trialDays: p.trial_days,
    maxApplications: p.max_applications, maxDocuments: p.max_documents, maxMessages: p.max_messages,
    isPublic: p.is_public, isActive: p.is_active, isFeatured: p.is_featured, highlightColor: p.highlight_color,
  };
}

function subToVM(s: RawSubscription): Subscription {
  const b = planBadge(s.plan_slug);
  const name = s.user_name || s.user_email || "Unknown";
  return {
    id: s.subscription_id, initials: initialsOf(name), avatarBg: colorOf(s.subscription_id || name),
    customerName: name, customerEmail: s.user_email || "—", userRole: s.user_role || "—",
    planName: s.plan_name || "—", planBg: b.bg, planColor: b.color,
    status: s.status || "—", started: fmtDate(s.current_period_start), nextBilling: fmtDate(s.current_period_end),
    trialEnd: fmtDate(s.trial_end), billingCycle: cap(s.billing_cycle || "—"), price: s.amount_display || "—",
    couponCode: s.coupon_code, discountDisplay: s.discount_display, paymentProcessor: s.payment_processor,
    assignedByAdmin: s.assigned_by_admin, created: fmtDate(s.created_at),
  };
}

/* ───────────── STATS ───────────── */

export const fetchPricingStats = async (): Promise<PricingStats> => {
  const res = await api.get("/admin/subscriptions/stats");
  const s = res.data as RawStats;
  return {
    totalSubscribers: s.total_subscribers ?? 0,
    mrrDisplay: s.mrr_display || `$${((s.mrr_cents ?? 0) / 100).toLocaleString()}`,
    mrrChangePct: s.mrr_change_pct ?? 0, arrDisplay: s.arr_display || "—",
    activeSubscribers: s.active_subscribers ?? 0, activeChangePct: s.active_change_pct ?? 0,
    trialSubscribers: s.trial_subscribers ?? 0, trialChangePct: s.trial_change_pct ?? 0,
    churnedThisMonth: s.churned_this_month ?? 0, churnRatePct: s.churn_rate_pct ?? 0,
    pastDueCount: s.past_due_count ?? 0, pausedCount: s.paused_count ?? 0,
  };
};

/* ───────────── PLANS ───────────── */

export const fetchPlans = async (): Promise<Plan[]> => {
  const res = await api.get("/admin/subscription-plans");
  const items: RawPlan[] = Array.isArray(res.data?.items) ? res.data.items : [];
  return items.sort((a, b) => a.display_order - b.display_order).map(planToVM);
};

export const fetchPlanById = async (id: string): Promise<Plan> => {
  const res = await api.get(`/admin/subscription-plans/${id}`);
  return planToVM(res.data as RawPlan);
};

export const createPlan = async (body: Record<string, unknown>): Promise<RawPlan> => {
  const res = await api.post("/admin/subscription-plans", body);
  return res.data as RawPlan;
};

export const updatePlan = async (id: string, body: Record<string, unknown>): Promise<RawPlan> => {
  const res = await api.patch(`/admin/subscription-plans/${id}`, body); // PATCH (confirmed)
  return res.data as RawPlan;
};

export const togglePlan = async (id: string): Promise<RawPlan> => {
  const res = await api.patch(`/admin/subscription-plans/${id}/toggle`);
  return res.data as RawPlan;
};

/* ───────────── SUBSCRIPTIONS ───────────── */

export const fetchActiveSubscriptions = async (
  params?: { search?: string; status?: string; plan_id?: string; page?: number; page_size?: number }
): Promise<ActiveSubscriptionsResponse> => {
  const query: Record<string, string | number> = {
    sort_by: "created_at", sort_order: "desc",
    page: params?.page ?? 1, page_size: params?.page_size ?? 20,
  };
  if (params?.search) query.search = params.search;
  if (params?.status) query.status = params.status;
  if (params?.plan_id) query.plan_id = params.plan_id;
  const res = await api.get("/admin/subscriptions", { params: query });
  const items: RawSubscription[] = Array.isArray(res.data?.items) ? res.data.items : [];
  return { subscriptions: items.map(subToVM), total: res.data?.total ?? items.length };
};

// Full detail incl. invoice history (raw passthrough — shape varies)
export const fetchSubscriptionById = async (id: string): Promise<any> => {
  const res = await api.get(`/admin/subscriptions/${id}`);
  return res.data;
};

export const changeSubscriptionPlan = async (
  id: string, body: { new_plan_id: string; billing_cycle: string; admin_notes?: string }
): Promise<any> => {
  const res = await api.patch(`/admin/subscriptions/${id}/change-plan`, body);
  return res.data;
};

export const cancelSubscription = async (id: string, body?: Record<string, unknown>): Promise<any> => {
  const res = await api.patch(`/admin/subscriptions/${id}/cancel`, body ?? {});
  return res.data;
};

export const assignSubscription = async (body: Record<string, unknown>): Promise<any> => {
  const res = await api.post("/admin/subscriptions/assign", body);
  return res.data;
};

export const exportSubscriptions = async (): Promise<Blob> => {
  // Real backend CSV export endpoint
  const res = await api.get("/admin/subscriptions/export", { responseType: "blob" });
  return res.data as Blob;
};

/* ───────────── COUPONS ─────────────
   NOTE: GET/POST /admin/coupons exist. The coupon ITEM shape + POST body schema
   weren't fully visible in Swagger, so the page maps coupon fields defensively and
   the create form sends conventional fields. If POST returns 422, send the
   "POST /admin/coupons" request-body Schema screenshot and we'll align field names. */

export const fetchCoupons = async (
  params?: { search?: string; is_active?: boolean; page?: number; page_size?: number }
): Promise<{ items: any[]; total: number }> => {
  const query: Record<string, string | number | boolean> = {
    page: params?.page ?? 1, page_size: params?.page_size ?? 20,
  };
  if (params?.search) query.search = params.search;
  if (params?.is_active != null) query.is_active = params.is_active;
  const res = await api.get("/admin/coupons", { params: query });
  return { items: Array.isArray(res.data?.items) ? res.data.items : [], total: res.data?.total ?? 0 };
};

export const createCoupon = async (body: Record<string, unknown>): Promise<any> => {
  const res = await api.post("/admin/coupons", body);
  return res.data;
};

export const toggleCoupon = async (id: string): Promise<any> => {
  const res = await api.patch(`/admin/coupons/${id}/toggle`);
  return res.data;
};

export const updateCoupon = async (id: string, body: Record<string, unknown>): Promise<any> => {
  const res = await api.patch(`/admin/coupons/${id}`, body);
  return res.data;
};

/* ───────────── PENDING (no backend endpoint yet) ───────────── */
// Pricing-tier config, payment gateways, billing-cycle toggles, and a recent-activity
// feed have no endpoints in Swagger. Return empty so the page shows clean empty states.

export const fetchPricingConfig = async (): Promise<PricingConfig | null> => null;
export const savePricingConfig = async (_c: PricingConfig): Promise<never> => {
  throw new Error("Pricing-config endpoint not available yet (backend pending).");
};
export const fetchGateways = async (): Promise<any[]> => [];
export const toggleGateway = async (_id: string, _connected: boolean): Promise<never> => {
  throw new Error("Gateway endpoint not available yet (backend pending).");
};
export const fetchBillingCycles = async (): Promise<any[]> => [];
export const fetchSubscriptionActivity = async (): Promise<any[]> => [];