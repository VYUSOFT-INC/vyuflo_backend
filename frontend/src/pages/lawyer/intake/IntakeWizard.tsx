// src/pages/lawyer/intake/IntakeWizard.tsx
//
// Client Intake — 5-step wizard shell.
// ACTIVE STEPS: 3 (Immigration) → 4 (Case Type) → 5 (Review & Submit)
// Steps 1 (Personal Info) and 2 (Employment) are intentionally skipped
// for this iteration. Sidebar still shows all 5 (matches Figma) but
// 1 & 2 render as "Skipped" placeholders if a user clicks them.
//
// Route: /lawyer/intake/:sessionId
// Entry: /lawyer/intake (landing page with "+ New Intake" modal)
//
// API: /intake/sessions/{id}, /intake/sessions/{id}/data,
//      /intake/sessions/{id}/save-draft, /intake/sessions/{id}/generate-link,
//      /intake/sessions/{id}/submit, /intake/visa-status-options

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { intakeApi } from '../../../api/lawyer/intake.api';
import type {
  IntakeData,
  IntakeSession,
  PreviousVisa,
  VisaStatusOption,
  StepNumber,
} from '../../../types/lawyer/intake.types';
import { EMPTY_INTAKE_DATA, EMPTY_PREVIOUS_VISA } from '../../../types/lawyer/intake.types';

/* ── Icon imports ───────────────────────────────────────────────────── */
import iconStepCheck    from '../../../assets/icons/lawyer-intake/step-check.svg';
import iconStepCurrent  from '../../../assets/icons/lawyer-intake/step-current.svg';
import iconStepPending  from '../../../assets/icons/lawyer-intake/step-pending.svg';
import iconLink         from '../../../assets/icons/lawyer-intake/link-icon.svg';
import iconPlusBlue     from '../../../assets/icons/lawyer-intake/plus-blue.svg';
import iconArrowRight   from '../../../assets/icons/lawyer-intake/arrow-right-white.svg';
import iconTrash        from '../../../assets/icons/lawyer-intake/trash-gray.svg';
import iconCopy         from '../../../assets/icons/lawyer-intake/copy-icon.svg';
import iconLogo         from '../../../assets/icons/plane-icon.svg';
import iconCheck        from '../../../assets/icons/common/check-circle-green.svg';

/* ── Step metadata ──────────────────────────────────────────────────── */
const STEPS: { num: StepNumber; title: string; subtitle: string }[] = [
  { num: 1, title: 'Personal Info', subtitle: 'Your details' },
  { num: 2, title: 'Employment',    subtitle: 'Work history' },
  { num: 3, title: 'Immigration',   subtitle: 'Current Step' },
  { num: 4, title: 'Case Type',     subtitle: 'Selection' },
  { num: 5, title: 'Review',        subtitle: 'Confirm & Submit' },
];

const ACTIVE_STEPS: StepNumber[] = [3, 4, 5];

/* ═══════════════════════════════════════════════════════════════════════
   PAGE
═══════════════════════════════════════════════════════════════════════ */
export default function IntakeWizard() {
  const { sessionId = '' } = useParams<{ sessionId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  /* URL ?step=N — default to 3 (the first active step) */
  const stepParam = Number(searchParams.get('step')) as StepNumber;
  const currentStep: StepNumber = ACTIVE_STEPS.includes(stepParam) ? stepParam : 3;

  const [session, setSession] = useState<IntakeSession | null>(null);
  const [data, setData] = useState<IntakeData>(EMPTY_INTAKE_DATA);
  const [visaOptions, setVisaOptions] = useState<VisaStatusOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<'idle' | 'saving' | 'saved'>('idle');
  const [caseVisaType, setCaseVisaType] = useState<string>(''); // Step 4 selection (UI-only — see note)
  const [linkModal, setLinkModal] = useState<{ url: string; expires: string } | null>(null);
  const [submitted, setSubmitted] = useState(false);

  /* ── Load session, intake data, visa options on mount ──────────────── */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!sessionId) {
        setError('No session ID provided. Open this page via "+ New Intake" on the Client Intake landing page.');
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const [sessionRes, dataRes, optsRes] = await Promise.all([
          intakeApi.getIntakeSession(sessionId),
          intakeApi.getIntakeData(sessionId).catch(() => null),
          intakeApi.getVisaStatusOptions().catch(() => ({ items: [] })),
        ]);
        if (cancelled) return;
        setSession(sessionRes);
        if (dataRes) setData({ ...EMPTY_INTAKE_DATA, ...dataRes });
        setVisaOptions(optsRes.items ?? []);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load session.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [sessionId]);

  /* ── Auto-save on blur (debounced) ─────────────────────────────────── */
  const autoSaveTimer = useRef<number | null>(null);
  const autoSave = useCallback((patch: Partial<IntakeData>) => {
    if (!sessionId) return;
    if (autoSaveTimer.current) window.clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = window.setTimeout(async () => {
      try {
        setSaving('saving');
        await intakeApi.saveIntakeData(sessionId, patch);
        setSaving('saved');
        window.setTimeout(() => setSaving('idle'), 1500);
      } catch {
        setSaving('idle');
      }
    }, 600);
  }, [sessionId]);

  /* ── Save Draft (top-right button) ─────────────────────────────────── */
  const handleSaveDraft = async () => {
    if (!sessionId) return;
    try {
      setSaving('saving');
      await intakeApi.saveIntakeData(sessionId, data);
      await intakeApi.saveDraft(sessionId);
      setSaving('saved');
      window.setTimeout(() => setSaving('idle'), 1500);
    } catch {
      setSaving('idle');
      alert('Could not save draft. Please try again.');
    }
  };

  /* ── Continue / Previous step navigation ───────────────────────────── */
  const goToStep = (n: StepNumber) => {
    searchParams.set('step', String(n));
    setSearchParams(searchParams);
  };

  const handleContinue = async () => {
    if (!sessionId) return;
    try {
      await intakeApi.saveIntakeData(sessionId, data, { step_completed: currentStep });
      // Move to next active step
      const idx = ACTIVE_STEPS.indexOf(currentStep);
      const next = ACTIVE_STEPS[idx + 1];
      if (next) goToStep(next);
    } catch {
      alert('Could not save this step. Please try again.');
    }
  };

  const handlePrevious = () => {
    const idx = ACTIVE_STEPS.indexOf(currentStep);
    const prev = ACTIVE_STEPS[idx - 1];
    if (prev) goToStep(prev);
  };

  /* ── Generate Link (Step 3) ───────────────────────────────────────── */
  const handleGenerateLink = async () => {
    if (!sessionId) return;
    try {
      const res = await intakeApi.generateClientLink(sessionId);
      setLinkModal({ url: res.client_url, expires: res.token_expires_at });
    } catch {
      alert('Could not generate client link.');
    }
  };

  /* ── Submit (Step 5) ──────────────────────────────────────────────── */
  const handleSubmit = async () => {
    if (!sessionId) return;
    if (!window.confirm('Submit this intake? You will not be able to edit it after submission.')) return;
    try {
      await intakeApi.submitIntake(sessionId);
      setSubmitted(true);
    } catch {
      alert('Could not submit. Please try again.');
    }
  };

  /* ── Step completion flags (drives sidebar checkmarks) ─────────────── */
  const stepDone = (n: StepNumber): boolean => {
    if (!session) return false;
    if (n === 1) return session.step_1_completed;
    if (n === 2) return session.step_2_completed;
    if (n === 3) return session.step_3_completed;
    if (n === 4) return session.step_4_completed;
    return session.step_5_completed;
  };

  /* ── Render ──────────────────────────────────────────────────────── */
  if (submitted) return <SubmittedScreen sessionId={sessionId} onBack={() => navigate('/lawyer/intake')} />;

  return (
    <div className="min-h-screen bg-slate-50" style={{ fontFamily: "'Inter', sans-serif" }}>
      {/* ── HEADER ──────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 sm:px-8">
        <button onClick={() => navigate('/lawyer/intake')} className="flex items-center gap-2">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-[10px] shadow-sm"
            style={{ backgroundImage: 'linear-gradient(135deg, rgb(37,99,235) 0%, rgb(147,51,234) 100%)' }}
          >
            <img src={iconLogo} alt="VisaFlow" className="h-[14px] w-[14px] object-contain" />
          </div>
          <span className="text-lg font-bold text-indigo-600">VisaFlow</span>
        </button>
        <div className="flex items-center gap-3 sm:gap-4">
          <button
            onClick={handleSaveDraft}
            disabled={loading || saving === 'saving'}
            className="text-sm font-medium text-gray-700 hover:text-indigo-600 disabled:opacity-50"
          >
            {saving === 'saving' ? 'Saving…' : saving === 'saved' ? 'Saved ✓' : 'Save Draft'}
          </button>
          <div className="h-8 w-8 shrink-0 rounded-full bg-indigo-100 ring-2 ring-white">
            <div className="flex h-full w-full items-center justify-center text-xs font-semibold text-indigo-700">L</div>
          </div>
        </div>
      </header>

      {/* ── MAIN ───────────────────────────────────────────────── */}
      <div className="mx-auto flex max-w-[1240px] flex-col gap-6 px-4 py-6 sm:px-6 lg:flex-row lg:gap-8 lg:px-8 lg:py-10">

        {/* Sidebar progress */}
        <ProgressSidebar
          currentStep={currentStep}
          stepDone={stepDone}
          onJump={(n) => ACTIVE_STEPS.includes(n) && goToStep(n)}
        />

        {/* Step content */}
        <main className="flex-1 min-w-0">
          {loading ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center text-sm text-gray-500">
              Loading session…
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
              {error}
            </div>
          ) : (
            <>
              {currentStep === 3 && (
                <Step3Immigration
                  data={data}
                  visaOptions={visaOptions}
                  onChange={(patch) => { setData((p) => ({ ...p, ...patch })); autoSave(patch); }}
                  onGenerateLink={handleGenerateLink}
                />
              )}
              {currentStep === 4 && (
                <Step4CaseType
                  visaOptions={visaOptions}
                  selected={caseVisaType}
                  onSelect={setCaseVisaType}
                />
              )}
              {currentStep === 5 && (
                <Step5Review
                  data={data}
                  caseVisaType={caseVisaType}
                  visaOptions={visaOptions}
                  onEdit={(n) => goToStep(n)}
                  onSubmit={handleSubmit}
                />
              )}

              {/* Nav buttons */}
              <NavButtons
                currentStep={currentStep}
                onPrevious={handlePrevious}
                onContinue={handleContinue}
                isLast={currentStep === 5}
              />
            </>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white py-4 text-center text-xs text-gray-500">
        © 2026 VisaFlow Inc. All rights reserved. Secure Intake Platform.
      </footer>

      {/* Generate Link result modal */}
      {linkModal && (
        <GenerateLinkModal
          url={linkModal.url}
          expires={linkModal.expires}
          onClose={() => setLinkModal(null)}
        />
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   PROGRESS SIDEBAR
═══════════════════════════════════════════════════════════════════════ */
function ProgressSidebar({
  currentStep,
  stepDone,
  onJump,
}: {
  currentStep: StepNumber;
  stepDone: (n: StepNumber) => boolean;
  onJump: (n: StepNumber) => void;
}) {
  return (
    <aside className="w-full lg:sticky lg:top-24 lg:w-[260px] lg:self-start">
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <p className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
          Application Progress
        </p>
        <div className="space-y-1">
          {STEPS.map((s, i) => {
            const done = stepDone(s.num);
            const isCurrent = s.num === currentStep;
            const clickable = ACTIVE_STEPS.includes(s.num);
            const icon = done ? iconStepCheck : isCurrent ? iconStepCurrent : iconStepPending;
            return (
              <div key={s.num} className="relative">
                <button
                  type="button"
                  onClick={() => clickable && onJump(s.num)}
                  disabled={!clickable}
                  className={`flex w-full items-start gap-3 rounded-lg px-2 py-2 text-left transition-colors ${
                    clickable ? 'hover:bg-indigo-50' : 'cursor-not-allowed opacity-60'
                  }`}
                >
                  <img src={icon} alt="" className="h-6 w-6 shrink-0" />
                  <div className="min-w-0">
                    <p className={`text-sm font-semibold ${isCurrent ? 'text-indigo-600' : 'text-gray-900'}`}>
                      {s.title}
                    </p>
                    <p className="text-xs text-gray-500">{s.subtitle}</p>
                  </div>
                </button>
                {i < STEPS.length - 1 && (
                  <div className="absolute left-[19px] top-[42px] hidden h-3 w-px bg-gray-200 lg:block" />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </aside>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   STEP 3 — IMMIGRATION HISTORY (Figma fidelity)
═══════════════════════════════════════════════════════════════════════ */
function Step3Immigration({
  data,
  visaOptions,
  onChange,
  onGenerateLink,
}: {
  data: IntakeData;
  visaOptions: VisaStatusOption[];
  onChange: (patch: Partial<IntakeData>) => void;
  onGenerateLink: () => void;
}) {
  const addVisa = () => onChange({ previous_visas: [...data.previous_visas, { ...EMPTY_PREVIOUS_VISA }] });
  const updateVisa = (i: number, patch: Partial<PreviousVisa>) => {
    const next = data.previous_visas.map((v, idx) => idx === i ? { ...v, ...patch } : v);
    onChange({ previous_visas: next });
  };
  const removeVisa = (i: number) => {
    onChange({ previous_visas: data.previous_visas.filter((_, idx) => idx !== i) });
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-indigo-600">Step 3 of 5</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">Immigration History</h1>
        <p className="mt-1 text-sm text-gray-500">
          Please provide details about your past and current visa statuses to help us assess your case accurately.
        </p>
      </div>

      {/* Current Status */}
      <Card title="Current Status">
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 sm:gap-6">
          <Field label="Current Visa Status" required>
            <select
              value={data.current_visa_status}
              onChange={(e) => onChange({ current_visa_status: e.target.value })}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">Select status…</option>
              {visaOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <Field label="Expiration Date" required>
            <input
              type="date"
              value={data.visa_expiration_date}
              onChange={(e) => onChange({ visa_expiration_date: e.target.value })}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </Field>
        </div>
      </Card>

      {/* Background Questions */}
      <Card title="Background Questions">
        <div className="space-y-5">
          <YesNoRow
            label="Have you ever been denied a visa?"
            hint="Includes any US visa application denial in the past."
            value={data.has_visa_denial}
            onChange={(v) => onChange({ has_visa_denial: v })}
          />
          {data.has_visa_denial && (
            <Field label="Please provide details of the denial">
              <textarea
                value={data.visa_denial_details}
                onChange={(e) => onChange({ visa_denial_details: e.target.value })}
                placeholder="Include dates, visa types, and reasons provided by the consulate…"
                rows={4}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </Field>
          )}
          <YesNoRow
            label="Have you ever overstayed a visa?"
            value={data.has_overstay}
            onChange={(v) => onChange({ has_overstay: v })}
          />
        </div>
      </Card>

      {/* Previous US Visas */}
      <Card title="Previous US Visas">
        <div className="space-y-4">
          {data.previous_visas.map((v, i) => (
            <PreviousVisaItem
              key={i}
              index={i}
              visa={v}
              visaOptions={visaOptions}
              onChange={(patch) => updateVisa(i, patch)}
              onRemove={() => removeVisa(i)}
            />
          ))}
          <button
            type="button"
            onClick={addVisa}
            className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 bg-white px-4 py-3 text-sm font-medium text-indigo-600 hover:border-indigo-400 hover:bg-indigo-50"
          >
            <img src={iconPlusBlue} alt="" className="h-4 w-4" />
            Add Another Visa
          </button>
        </div>
      </Card>

      {/* Generate Link */}
      <div className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-gray-900">Need the client to fill this out?</p>
          <p className="mt-0.5 text-xs text-gray-500">Generate a secure link to send to your client for data entry.</p>
        </div>
        <button
          type="button"
          onClick={onGenerateLink}
          className="flex shrink-0 items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <img src={iconLink} alt="" className="h-4 w-4" />
          Generate Link
        </button>
      </div>
    </div>
  );
}

function PreviousVisaItem({
  index,
  visa,
  visaOptions,
  onChange,
  onRemove,
}: {
  index: number;
  visa: PreviousVisa;
  visaOptions: VisaStatusOption[];
  onChange: (patch: Partial<PreviousVisa>) => void;
  onRemove: () => void;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50/50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Visa #{index + 1}</p>
        <button type="button" onClick={onRemove} className="rounded-md p-1 hover:bg-red-50">
          <img src={iconTrash} alt="Remove" className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Visa Type">
          <select
            value={visa.visa_type}
            onChange={(e) => onChange({ visa_type: e.target.value })}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">Select…</option>
            {visaOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </Field>
        <Field label="Visa Number">
          <input
            type="text"
            value={visa.visa_number}
            onChange={(e) => onChange({ visa_number: e.target.value })}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </Field>
        <Field label="Issue Date">
          <input
            type="date"
            value={visa.issue_date}
            onChange={(e) => onChange({ issue_date: e.target.value })}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </Field>
        <Field label="Expiry Date">
          <input
            type="date"
            value={visa.expiry_date}
            onChange={(e) => onChange({ expiry_date: e.target.value })}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Issuing Country">
            <input
              type="text"
              value={visa.issuing_country}
              onChange={(e) => onChange({ issuing_country: e.target.value })}
              placeholder="e.g. United States"
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </Field>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   STEP 4 — CASE TYPE SELECTION
═══════════════════════════════════════════════════════════════════════ */
function Step4CaseType({
  visaOptions,
  selected,
  onSelect,
}: {
  visaOptions: VisaStatusOption[];
  selected: string;
  onSelect: (v: string) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-indigo-600">Step 4 of 5</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">Case Type</h1>
        <p className="mt-1 text-sm text-gray-500">
          Select the visa category you are applying for. Choose the type that best matches your case.
        </p>
      </div>

      {visaOptions.length === 0 ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          No visa types available. Backend may be offline.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visaOptions.map((o) => {
            const isSelected = selected === o.value;
            return (
              <button
                key={o.value}
                type="button"
                onClick={() => onSelect(o.value)}
                className={`relative rounded-xl border-2 bg-white p-5 text-left transition-all ${
                  isSelected ? 'border-indigo-600 ring-2 ring-indigo-100' : 'border-gray-200 hover:border-indigo-300'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-lg font-bold text-gray-900">{o.value}</p>
                  {isSelected && (
                    <div className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600">
                      <svg viewBox="0 0 20 20" fill="white" className="h-3 w-3"><path d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 9.7a1 1 0 011.4-1.4l3.8 3.8 6.8-6.8a1 1 0 011.4 0z"/></svg>
                    </div>
                  )}
                </div>
                <p className="mt-1 text-sm text-gray-600">{o.label}</p>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   STEP 5 — REVIEW & SUBMIT
═══════════════════════════════════════════════════════════════════════ */
function Step5Review({
  data,
  caseVisaType,
  visaOptions,
  onEdit,
  onSubmit,
}: {
  data: IntakeData;
  caseVisaType: string;
  visaOptions: VisaStatusOption[];
  onEdit: (n: StepNumber) => void;
  onSubmit: () => void;
}) {
  const labelFor = (v: string) => visaOptions.find((o) => o.value === v)?.label ?? v ?? '—';

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-indigo-600">Step 5 of 5</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">Review & Submit</h1>
        <p className="mt-1 text-sm text-gray-500">
          Please verify all information below. Once submitted, the application cannot be edited.
        </p>
      </div>

      {/* Immigration History summary */}
      <Card
        title="Immigration History"
        action={
          <button onClick={() => onEdit(3)} className="text-xs font-semibold text-indigo-600 hover:text-indigo-700">
            Edit
          </button>
        }
      >
        <Dl>
          <Dt label="Current Visa Status" value={labelFor(data.current_visa_status)} />
          <Dt label="Expiration Date" value={data.visa_expiration_date || '—'} />
          <Dt label="Visa Denial" value={data.has_visa_denial ? `Yes — ${data.visa_denial_details || 'No details'}` : 'No'} />
          <Dt label="Overstayed" value={data.has_overstay ? 'Yes' : 'No'} />
          <Dt label="Previous Visas" value={`${data.previous_visas.length} visa(s) on record`} />
        </Dl>
        {data.previous_visas.length > 0 && (
          <div className="mt-3 space-y-2 border-t border-gray-100 pt-3 text-xs text-gray-600">
            {data.previous_visas.map((v, i) => (
              <p key={i}>
                #{i + 1}: <span className="font-medium">{labelFor(v.visa_type)}</span> ({v.visa_number || '—'})
                {' · '}Issued {v.issue_date || '—'}, Expires {v.expiry_date || '—'}
                {v.issuing_country && ` · ${v.issuing_country}`}
              </p>
            ))}
          </div>
        )}
      </Card>

      {/* Case Type summary */}
      <Card
        title="Case Type"
        action={
          <button onClick={() => onEdit(4)} className="text-xs font-semibold text-indigo-600 hover:text-indigo-700">
            Edit
          </button>
        }
      >
        {caseVisaType ? (
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-indigo-50 px-3 py-1.5">
              <span className="text-base font-bold text-indigo-700">{caseVisaType}</span>
            </div>
            <span className="text-sm text-gray-700">{labelFor(caseVisaType)}</span>
          </div>
        ) : (
          <p className="text-sm text-amber-700">⚠️ No case type selected. Go back to Step 4 to choose.</p>
        )}
      </Card>

      {/* Submit notice */}
      <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-5">
        <p className="text-sm font-semibold text-indigo-900">Ready to submit?</p>
        <p className="mt-1 text-xs text-indigo-700">
          By submitting, you confirm all information is accurate. The intake will be locked and routed to the attorney.
        </p>
        <button
          onClick={onSubmit}
          disabled={!caseVisaType}
          className="mt-3 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Submit Application
        </button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   SUBMITTED — success screen
═══════════════════════════════════════════════════════════════════════ */
function SubmittedScreen({ sessionId, onBack }: { sessionId: string; onBack: () => void }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
          <img src={iconCheck} alt="" className="h-10 w-10" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Application Submitted</h2>
        <p className="mt-2 text-sm text-gray-500">
          Session <span className="font-mono text-xs">{sessionId.slice(0, 8)}…</span> has been submitted and locked.
        </p>
        <button
          onClick={onBack}
          className="mt-6 w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
        >
          Back to Client Intake
        </button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   GENERATE LINK MODAL
═══════════════════════════════════════════════════════════════════════ */
function GenerateLinkModal({
  url,
  expires,
  onClose,
}: {
  url: string;
  expires: string;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-xl">
        <h3 className="text-lg font-bold text-gray-900">Client Link Generated</h3>
        <p className="mt-1 text-sm text-gray-500">
          Send this link to your client. It expires on{' '}
          <span className="font-medium">{new Date(expires).toLocaleDateString()}</span>.
        </p>
        <div className="mt-4 flex items-stretch gap-2">
          <input
            readOnly
            value={url}
            className="flex-1 min-w-0 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 font-mono text-xs text-gray-700"
          />
          <button
            onClick={handleCopy}
            className="flex shrink-0 items-center gap-1 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
          >
            <img src={iconCopy} alt="" className="h-3 w-3 brightness-0 invert" />
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <button
          onClick={onClose}
          className="mt-4 w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Done
        </button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   NAV BUTTONS
═══════════════════════════════════════════════════════════════════════ */
function NavButtons({
  currentStep,
  onPrevious,
  onContinue,
  isLast,
}: {
  currentStep: StepNumber;
  onPrevious: () => void;
  onContinue: () => void;
  isLast: boolean;
}) {
  const canGoBack = ACTIVE_STEPS.indexOf(currentStep) > 0;
  return (
    <div className="mt-6 flex items-center justify-between gap-3 border-t border-gray-100 pt-6">
      <button
        type="button"
        onClick={onPrevious}
        disabled={!canGoBack}
        className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Previous
      </button>
      {!isLast && (
        <button
          type="button"
          onClick={onContinue}
          className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md hover:opacity-90"
        >
          Continue
          <img src={iconArrowRight} alt="" className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   SHARED PRIMITIVES
═══════════════════════════════════════════════════════════════════════ */
function Card({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
        <h3 className="text-base font-semibold text-gray-900">{title}</h3>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-gray-700">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      {children}
    </div>
  );
}

function YesNoRow({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-900">{label}</p>
        {hint && <p className="mt-0.5 text-xs text-gray-500">{hint}</p>}
      </div>
      <div className="flex shrink-0 rounded-lg border border-gray-300 bg-white p-1">
        <button
          type="button"
          onClick={() => onChange(true)}
          className={`rounded-md px-4 py-1 text-xs font-semibold transition-colors ${
            value ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          Yes
        </button>
        <button
          type="button"
          onClick={() => onChange(false)}
          className={`rounded-md px-4 py-1 text-xs font-semibold transition-colors ${
            !value ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          No
        </button>
      </div>
    </div>
  );
}

function Dl({ children }: { children: React.ReactNode }) {
  return <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">{children}</dl>;
}

function Dt({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-gray-900">{value}</dd>
    </div>
  );
}
