// src/pages/employee/PaymentsScreen.tsx

import { useState, useMemo } from "react";
import {
  useOutstandingFees,
  usePaymentHistory,
  usePaymentMethods,
  usePayFee,
  usePayAllFees,
} from "../../hooks/employee/usePayments";
import { formatCents } from "../../types/employee/payment.types";
import type { Fee, PaymentMethod, Payment } from "../../types/employee/payment.types";
import { PageHeader, PageContent } from "../../components/layout/Pageheader";

// ── Icons ─────────────────────────────────────────────────────────────────────

const IconDocument = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <rect x="3" y="2" width="14" height="16" rx="2" stroke="#4F46E5" strokeWidth="1.5"/>
    <path d="M7 7h6M7 10h6M7 13h4" stroke="#4F46E5" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);
const IconFileAlt = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <rect x="3" y="2" width="14" height="16" rx="2" stroke="#7C3AED" strokeWidth="1.5"/>
    <path d="M7 7h6M7 10h6M7 13h4" stroke="#7C3AED" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);
const IconAlert = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
    <circle cx="6" cy="6" r="5" fill="#EF4444"/>
    <path d="M6 3.5v3M6 8h.01" stroke="white" strokeWidth="1.3" strokeLinecap="round"/>
  </svg>
);
const IconClock = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
    <circle cx="6" cy="6" r="5" stroke="#F59E0B" strokeWidth="1.3"/>
    <path d="M6 3.5V6l1.5 1" stroke="#F59E0B" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
const IconLock = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <rect x="2" y="6" width="10" height="7" rx="1.5" stroke="white" strokeWidth="1.3"/>
    <path d="M4.5 6V4.5a2.5 2.5 0 015 0V6" stroke="white" strokeWidth="1.3" strokeLinecap="round"/>
  </svg>
);
const IconShield = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M7 1.5L2 3.5v3.5c0 3 2.5 5.5 5 6 2.5-.5 5-3 5-6V3.5L7 1.5z" stroke="#6B7280" strokeWidth="1.2" strokeLinejoin="round"/>
    <path d="M4.5 7l2 2 3-3" stroke="#6B7280" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
const IconVisa = () => (
  <svg width="36" height="22" viewBox="0 0 36 22" fill="none">
    <rect width="36" height="22" rx="3" fill="#1A1F71"/>
    <path d="M14 15l2-8h2.5L16.5 15H14zM24.5 7.2c-.5-.2-1.2-.4-2.2-.4-2.4 0-4.1 1.2-4.1 3 0 1.3 1.2 2 2.2 2.4 1 .4 1.3.7 1.3 1.1 0 .6-.8 1-1.6 1-1 0-1.6-.1-2.4-.5l-.4-.2-.3 2c.6.2 1.7.5 2.8.5 2.6 0 4.3-1.2 4.3-3.1 0-1-.6-1.8-2.1-2.5-.9-.4-1.4-.7-1.4-1.1 0-.4.4-.8 1.4-.8.8 0 1.4.1 1.9.3l.2.1.4-2.1zM28 7h-1.9c-.6 0-1 .2-1.3.7L21.5 15h2.6l.5-1.4h3.2l.3 1.4H30L28 7zm-3 4.8l1-2.7.5 2.7h-1.5zM11.5 7L9.2 12.5 9 11.4C8.6 9.9 7.3 8.5 5.8 7.7L8 15h2.7L14.3 7h-2.8z" fill="white"/>
  </svg>
);
const IconMastercard = () => (
  <svg width="36" height="22" viewBox="0 0 36 22" fill="none">
    <rect width="36" height="22" rx="3" fill="#252525"/>
    <circle cx="14" cy="11" r="6" fill="#EB001B"/>
    <circle cx="22" cy="11" r="6" fill="#F79E1B"/>
    <path d="M18 6.5a6 6 0 010 9 6 6 0 010-9z" fill="#FF5F00"/>
  </svg>
);
const IconPayPal = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <path d="M8.5 17H6.5l2.5-12h5c3 0 4.5 1.5 4 4.5C17.5 12 15 13.5 12 13.5H10L8.5 17z" fill="#003087"/>
    <path d="M10.5 20H8.5l1-4H11c3 0 5-1.8 4.5-4.5C15 9 13 7.5 10.5 7.5" fill="#009CDE"/>
  </svg>
);
const IconApple = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <path d="M14.94 5.19A4.38 4.38 0 0016 2a4.44 4.44 0 00-3 1.52 4.17 4.17 0 00-1 3.09 3.69 3.69 0 002.94-1.42z" fill="#1D1D1F"/>
    <path d="M16.52 7.6c-1.62 0-2.3.77-3.43.77-1.16 0-2.05-.77-3.46-.77-1.38 0-2.85.84-3.78 2.27C4.4 11.7 4.67 14.74 6.3 17.27c.59.9 1.37 1.93 2.4 1.94.92.01 1.18-.58 2.44-.59 1.26-.01 1.5.6 2.42.59 1.03-.01 1.85-1.14 2.44-2.04.42-.64.58-1 .9-1.75-2.36-.9-2.74-4.24-.4-5.54-.79-1-1.96-1.28-2.98-1.28z" fill="#1D1D1F"/>
  </svg>
);
const IconPlus = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M7 2.5v9M2.5 7h9" stroke="#4F46E5" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);
const IconDownload = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M7 2v7M4.5 6.5L7 9l2.5-2.5" stroke="#6B7280" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M2 11h10" stroke="#6B7280" strokeWidth="1.3" strokeLinecap="round"/>
  </svg>
);

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  return Math.ceil((new Date(iso).getTime() - Date.now()) / 86400000);
}
function getStatusPill(status: Payment["status"]) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    completed:          { bg: "bg-[#ECFDF5]", text: "text-[#059669]", label: "Paid" },
    pending:            { bg: "bg-[#FFF7ED]", text: "text-[#C2410C]", label: "Pending" },
    processing:         { bg: "bg-[#EFF6FF]", text: "text-[#2563EB]", label: "Processing" },
    failed:             { bg: "bg-[#FEF2F2]", text: "text-[#DC2626]", label: "Failed" },
    cancelled:          { bg: "bg-[#F3F4F6]", text: "text-[#6B7280]", label: "Cancelled" },
    refunded:           { bg: "bg-[#F5F3FF]", text: "text-[#7C3AED]", label: "Refunded" },
    partially_refunded: { bg: "bg-[#F5F3FF]", text: "text-[#7C3AED]", label: "Partial Refund" },
  };
  const s = map[status] ?? { bg: "bg-[#F3F4F6]", text: "text-[#6B7280]", label: status };
  return (
    <span className={`inline-flex items-center px-[8px] py-[3px] rounded-full text-[11px] font-semibold ${s.bg} ${s.text}`}>
      {s.label}
    </span>
  );
}

// ── Fee Card ──────────────────────────────────────────────────────────────────

function FeeCard({ fee, selectedMethodId, onPay, paying, index }: {
  fee: Fee; selectedMethodId: string | null;
  onPay: (id: string) => void; paying: boolean; index: number;
}) {
  const days = daysUntil(fee.due_date);
  const isOverdue = fee.status === "overdue" || (days !== null && days < 0);
  const isUrgent  = fee.is_urgent || (days !== null && days <= 3 && days >= 0);

  return (
    <div className="bg-white rounded-[12px] border border-[#E5E7EB] p-[16px] sm:p-[20px]">
      {/* Top row — stacks on very small screens */}
      <div className="flex items-start justify-between gap-[12px]">
        <div className="flex items-start gap-[12px] sm:gap-[14px] flex-1 min-w-0">
          <div className={`w-[38px] h-[38px] sm:w-[40px] sm:h-[40px] rounded-[10px] flex items-center justify-center flex-shrink-0 ${
            index % 2 === 0 ? "bg-[#EEF2FF]" : "bg-[#F5F3FF]"
          }`}>
            {index % 2 === 0 ? <IconDocument /> : <IconFileAlt />}
          </div>
          <div className="min-w-0">
            <p className="text-[14px] sm:text-[15px] font-semibold text-[#111827] leading-tight">{fee.title}</p>
            <p className="text-[11px] sm:text-[12px] text-[#9CA3AF] mt-[2px]">
              Case ID: {fee.application_id ? `VF-${String(fee.application_id).slice(0, 8).toUpperCase()}` : "—"}
            </p>
          </div>
        </div>
        {/* Amount + button — wrap on very narrow */}
        <div className="flex flex-col sm:flex-row items-end sm:items-center gap-[8px] sm:gap-[16px] flex-shrink-0">
          <p className="text-[18px] sm:text-[20px] font-bold text-[#111827]">{formatCents(fee.amount_usd)}</p>
          <button
            onClick={() => onPay(fee.id)}
            disabled={paying || !selectedMethodId}
            className="px-[14px] sm:px-[20px] py-[8px] sm:py-[9px] rounded-[8px] bg-gradient-to-r from-[#4F46E5] to-[#7C3AED] text-white text-[12px] sm:text-[13px] font-semibold hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity whitespace-nowrap"
          >
            {paying ? "Processing..." : "Pay Now"}
          </button>
        </div>
      </div>
      {fee.due_date && (
        <div className="mt-[12px] sm:mt-[14px]">
          {isOverdue || isUrgent ? (
            <span className={`inline-flex items-center gap-[5px] text-[11px] font-medium px-[10px] py-[4px] rounded-full ${
              isOverdue ? "bg-[#FEF2F2] text-[#DC2626]" : "bg-[#FEF3C7] text-[#92400E]"
            }`}>
              {isOverdue ? <IconAlert /> : <IconClock />}
              {isOverdue ? "Urgent: " : ""}Due {formatDate(fee.due_date)}
            </span>
          ) : (
            <span className="inline-flex items-center gap-[5px] text-[11px] font-medium px-[10px] py-[4px] rounded-full bg-[#FFF7ED] text-[#B45309]">
              <IconClock />Due {formatDate(fee.due_date)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ── Payment Method Tile ───────────────────────────────────────────────────────

function MethodTile({ method, selected, onSelect }: {
  method: PaymentMethod; selected: boolean; onSelect: () => void;
}) {
  const isCard   = method.method_type === "credit_card" || method.method_type === "debit_card";
  const isPaypal = method.method_type === "paypal";
  const isApple  = method.method_type === "apple_pay";
  return (
    <button onClick={onSelect}
      className={`relative flex flex-col items-center justify-center gap-[8px] rounded-[12px] border-2 p-[12px] sm:p-[16px] min-h-[72px] sm:min-h-[80px] transition-all ${
        selected ? "border-[#4F46E5] bg-[#F5F3FF]" : "border-[#E5E7EB] bg-white hover:border-[#C4B5FD]"
      }`}>
      <div className={`absolute top-[8px] right-[8px] sm:top-[10px] sm:right-[10px] w-[14px] h-[14px] sm:w-[16px] sm:h-[16px] rounded-full border-2 flex items-center justify-center ${
        selected ? "border-[#4F46E5]" : "border-[#D1D5DB]"
      }`}>
        {selected && <div className="w-[6px] h-[6px] sm:w-[7px] sm:h-[7px] rounded-full bg-[#4F46E5]" />}
      </div>
      {isCard   && <div className="flex items-center gap-[2px] sm:gap-[4px]"><IconVisa /><IconMastercard /></div>}
      {isPaypal && <IconPayPal />}
      {isApple  && <IconApple />}
      <span className="text-[11px] sm:text-[12px] font-medium text-[#374151]">
        {isCard ? "Credit Card" : isPaypal ? "PayPal" : "Apple Pay"}
      </span>
    </button>
  );
}

const MOCK_METHOD_TILES = [
  { id: "mock-cc", type: "credit_card", label: "Credit Card" },
  { id: "mock-pp", type: "paypal",      label: "PayPal"      },
  { id: "mock-ap", type: "apple_pay",   label: "Apple Pay"   },
];

// ── Payment History Row ───────────────────────────────────────────────────────

function PaymentHistoryRow({ payment }: { payment: Payment }) {
  return (
    <div className="flex items-center gap-[10px] sm:gap-[12px] py-[12px] sm:py-[14px] border-b border-[#F3F4F6] last:border-0">
      <div className="w-[32px] h-[32px] sm:w-[36px] sm:h-[36px] rounded-[8px] bg-[#F3F4F6] flex items-center justify-center text-[#6B7280] flex-shrink-0">
        <IconDocument />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] sm:text-[13px] font-medium text-[#111827] truncate">
          {payment.description ?? "Payment"}
        </p>
        <p className="text-[10px] sm:text-[11px] text-[#9CA3AF] mt-[2px]">
          {formatDate(payment.completed_at ?? payment.created_at)}
          {payment.card_last4_snapshot && ` · •••• ${payment.card_last4_snapshot}`}
        </p>
      </div>
      <div className="flex flex-col items-end gap-[4px] flex-shrink-0">
        <span className="text-[13px] sm:text-[14px] font-semibold text-[#111827]">{formatCents(payment.amount_usd)}</span>
        {getStatusPill(payment.status)}
      </div>
      {payment.gateway_receipt_url && (
        <a href={payment.gateway_receipt_url} target="_blank" rel="noopener noreferrer"
          className="p-[6px] rounded-[6px] text-[#9CA3AF] hover:text-[#374151] hover:bg-[#F3F4F6] transition-colors flex-shrink-0">
          <IconDownload />
        </a>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type Tab = "outstanding" | "history";

export default function PaymentsScreen() {
  const [activeTab,       setActiveTab]       = useState<Tab>("outstanding");
  const [selectedMethodId, setSelectedMethodId] = useState<string | null>(null);
  const [mockSelected,    setMockSelected]    = useState("mock-cc");

  const { fees, loading: feesLoading, error: feesError, refetch: refetchFees, totalDue } = useOutstandingFees();
  const { payments, loading: paymentsLoading } = usePaymentHistory();
  const { methods,  loading: methodsLoading  } = usePaymentMethods();

  const { submit: submitPayFee, loading: payingOne } = usePayFee(refetchFees);
  const { submit: submitPayAll, loading: payingAll } = usePayAllFees(refetchFees);

  const activeMethods = methods.filter(m => m.is_active);

  const effectiveSelectedId = useMemo(() => {
    if (selectedMethodId) return selectedMethodId;
    const def = activeMethods.find(m => m.is_default);
    return def?.id ?? activeMethods[0]?.id ?? null;
  }, [selectedMethodId, activeMethods]);

  const handlePayFee = (feeId: string) => {
    if (!effectiveSelectedId) return;
    submitPayFee({ fee_id: feeId, payment_method_id: effectiveSelectedId });
  };
  const handlePayAll = () => {
    if (fees.length === 0) return;
    if (effectiveSelectedId)
      submitPayAll({ fee_ids: fees.map(f => f.id), payment_method_id: effectiveSelectedId });
  };

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "outstanding", label: "Outstanding Fees", count: fees.length },
    { key: "history",     label: "Payment History" },
  ];

  return (
    <div className="flex flex-col h-full">

      {/* ── PageHeader — sticky, handles mobile logo ── */}
      <PageHeader
        title="Payments & Billing"
        subtitle="Manage your fees and payment history"
        showSearch={false}
      />

      {/* ── PageContent — this is the scrollable area ── */}
      <PageContent>
        <div className="flex flex-col gap-[20px] sm:gap-[24px] lg:gap-[28px]">

          {/* ── Tabs ── */}
          <div className="flex items-center border-b border-[#E5E7EB] -mx-[16px] sm:-mx-[24px] lg:-mx-[32px] px-[16px] sm:px-[24px] lg:px-[32px]">
            {tabs.map(tab => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-[6px] px-[4px] pb-[12px] mr-[20px] sm:mr-[28px] text-[13px] sm:text-[14px] font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? "border-[#4F46E5] text-[#4F46E5]"
                    : "border-transparent text-[#6B7280] hover:text-[#374151]"
                }`}>
                {tab.label}
                {typeof tab.count === "number" && tab.count > 0 && (
                  <span className={`text-[11px] px-[7px] py-[1px] rounded-full font-semibold ${
                    activeTab === tab.key ? "bg-[#EEF2FF] text-[#4F46E5]" : "bg-[#F3F4F6] text-[#6B7280]"
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* ── Outstanding Fees Tab ── */}
          {activeTab === "outstanding" && (
            <div className="flex flex-col xl:flex-row gap-[20px] sm:gap-[24px] items-start">

              {/* Left: fee cards + payment methods */}
              <div className="flex flex-col gap-[14px] sm:gap-[16px] flex-1 min-w-0 w-full">

                {/* Fee Cards */}
                {feesLoading ? (
                  <div className="flex items-center justify-center py-[48px] sm:py-[64px]">
                    <div className="w-[32px] h-[32px] border-2 border-[#E5E7EB] border-t-[#4F46E5] rounded-full animate-spin" />
                  </div>
                ) : feesError ? (
                  <div className="flex items-center justify-center py-[48px] sm:py-[64px]">
                    <p className="text-[14px] text-[#DC2626]">{feesError}</p>
                  </div>
                ) : fees.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-[48px] sm:py-[64px] gap-[12px] bg-white rounded-[12px] border border-[#E5E7EB]">
                    <div className="w-[48px] h-[48px] rounded-full bg-[#F0FDF4] flex items-center justify-center">
                      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                        <path d="M4 10l4 4 8-8" stroke="#059669" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                    <p className="text-[15px] font-semibold text-[#111827]">All caught up!</p>
                    <p className="text-[13px] text-[#6B7280]">You have no outstanding fees at this time.</p>
                  </div>
                ) : (
                  fees.map((fee, i) => (
                    <FeeCard key={fee.id} fee={fee} selectedMethodId={effectiveSelectedId}
                      onPay={handlePayFee} paying={payingOne} index={i} />
                  ))
                )}

                {/* Payment Methods */}
                <div className="bg-white rounded-[12px] border border-[#E5E7EB] p-[16px] sm:p-[20px] mt-[4px] sm:mt-[8px]">
                  <div className="flex items-center justify-between mb-[14px] sm:mb-[16px]">
                    <h2 className="text-[14px] sm:text-[15px] font-semibold text-[#111827]">Payment Methods</h2>
                    <button className="flex items-center gap-[4px] text-[12px] sm:text-[13px] font-medium text-[#4F46E5] hover:text-[#4338CA] transition-colors">
                      <IconPlus />Add New
                    </button>
                  </div>
                  {methodsLoading ? (
                    <div className="flex items-center justify-center py-[24px]">
                      <div className="w-[24px] h-[24px] border-2 border-[#E5E7EB] border-t-[#4F46E5] rounded-full animate-spin" />
                    </div>
                  ) : activeMethods.length > 0 ? (
                    <div className="grid grid-cols-3 gap-[10px] sm:gap-[12px]">
                      {activeMethods.map(m => (
                        <MethodTile key={m.id} method={m} selected={effectiveSelectedId === m.id}
                          onSelect={() => setSelectedMethodId(m.id)} />
                      ))}
                    </div>
                  ) : (
                    <div className="grid grid-cols-3 gap-[10px] sm:gap-[12px]">
                      {MOCK_METHOD_TILES.map(tile => (
                        <button key={tile.id} onClick={() => setMockSelected(tile.id)}
                          className={`relative flex flex-col items-center justify-center gap-[6px] sm:gap-[8px] rounded-[12px] border-2 p-[10px] sm:p-[16px] min-h-[70px] sm:min-h-[80px] transition-all ${
                            mockSelected === tile.id ? "border-[#4F46E5] bg-[#F5F3FF]" : "border-[#E5E7EB] bg-white hover:border-[#C4B5FD]"
                          }`}>
                          <div className={`absolute top-[8px] right-[8px] w-[14px] h-[14px] sm:w-[16px] sm:h-[16px] rounded-full border-2 flex items-center justify-center ${
                            mockSelected === tile.id ? "border-[#4F46E5]" : "border-[#D1D5DB]"
                          }`}>
                            {mockSelected === tile.id && <div className="w-[6px] h-[6px] rounded-full bg-[#4F46E5]" />}
                          </div>
                          {tile.type === "credit_card" && <div className="flex items-center gap-[2px]"><IconVisa /><IconMastercard /></div>}
                          {tile.type === "paypal"      && <IconPayPal />}
                          {tile.type === "apple_pay"   && <IconApple />}
                          <span className="text-[11px] sm:text-[12px] font-medium text-[#374151]">{tile.label}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Right: Payment Summary — full width on mobile, sidebar on xl */}
              <div className="bg-white rounded-[12px] border border-[#E5E7EB] p-[16px] sm:p-[20px] lg:p-[24px]
                              flex flex-col gap-[14px] sm:gap-[16px] w-full xl:w-[300px] xl:shrink-0">
                <h2 className="text-[15px] sm:text-[16px] font-bold text-[#111827]">Payment Summary</h2>
                <div className="flex flex-col gap-[8px] sm:gap-[10px]">
                  {fees.length === 0 ? (
                    <p className="text-[13px] text-[#9CA3AF]">No outstanding fees</p>
                  ) : (
                    fees.map(fee => (
                      <div key={fee.id} className="flex items-center justify-between gap-[8px]">
                        <span className="text-[12px] sm:text-[13px] text-[#374151] truncate flex-1">
                          {fee.title.replace(" Fee", "")}
                        </span>
                        <span className="text-[12px] sm:text-[13px] font-medium text-[#111827] flex-shrink-0">
                          {formatCents(fee.amount_usd)}
                        </span>
                      </div>
                    ))
                  )}
                </div>
                <div className="border-t border-[#E5E7EB]" />
                <div className="flex items-center justify-between">
                  <span className="text-[13px] sm:text-[14px] font-semibold text-[#111827]">Total Fees Due</span>
                  <span className="text-[18px] sm:text-[20px] font-bold text-[#4F46E5]">{formatCents(totalDue)}</span>
                </div>
                <button onClick={handlePayAll} disabled={payingAll || fees.length === 0}
                  className="w-full flex items-center justify-center gap-[8px] py-[12px] sm:py-[13px] rounded-[10px] bg-gradient-to-r from-[#4F46E5] to-[#7C3AED] text-white text-[13px] sm:text-[14px] font-semibold hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity">
                  <IconLock />
                  {payingAll ? "Processing..." : "Pay All Securely"}
                </button>
                <div className="flex items-center justify-center gap-[6px]">
                  <IconShield />
                  <span className="text-[10px] sm:text-[11px] text-[#9CA3AF]">256-bit SSL Encrypted Payment</span>
                </div>
              </div>
            </div>
          )}

          {/* ── Payment History Tab ── */}
          {activeTab === "history" && (
            paymentsLoading ? (
              <div className="flex items-center justify-center py-[48px] sm:py-[64px]">
                <div className="w-[32px] h-[32px] border-2 border-[#E5E7EB] border-t-[#4F46E5] rounded-full animate-spin" />
              </div>
            ) : payments.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-[48px] sm:py-[64px] gap-[8px]">
                <p className="text-[15px] font-semibold text-[#111827]">No payments yet</p>
                <p className="text-[13px] text-[#6B7280]">Your payment history will appear here.</p>
              </div>
            ) : (
              <div className="bg-white rounded-[12px] border border-[#E5E7EB] px-[16px] sm:px-[20px]">
                {payments.map(p => <PaymentHistoryRow key={p.id} payment={p} />)}
              </div>
            )
          )}

        </div>
      </PageContent>
    </div>
  );
}