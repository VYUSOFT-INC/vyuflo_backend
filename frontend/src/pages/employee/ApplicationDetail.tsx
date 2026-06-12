// src/pages/employee/ApplicationDetail.tsx
import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useApplication, useApplicationTasks } from "../../hooks/employee/useApplications";
import messageApi from "../../api/employee/message.api";
import type { Task, ApplicationStage } from "../../types/employee/application.types";
import documentsApi from "../../api/employee/documents.api";
import { PageHeader, PageContent } from "../../components/layout/Pageheader";

// ── Assets ────────────────────────────────────────────────────────────────────
import imgBreadArrow from "../../assets/icons/appdetail-breadarrow.svg";
import imgCheck      from "../../assets/icons/appdetail-check.svg";
import imgPdfIcon    from "../../assets/icons/appdetail-pdf-icon.svg";
import imgMsgIcon    from "../../assets/icons/appdetail-msg-icon.svg";
import imgArrowRight from "../../assets/icons/appdetail-arrow-right.svg";

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtDate(iso?: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
function fmtFileSize(bytes?: number): string {
  if (!bytes) return "";
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
function getStatusBadge(status: string) {
  switch (status) {
    case "approved":      return { bg: "bg-[#ecfdf5]", border: "border-[#d1fae5]", text: "text-[#059669]", label: "Approved" };
    case "in_progress":
    case "submitted":     return { bg: "bg-[#f0f5ff]", border: "border-[#e5edff]", text: "text-[#3a46e5]", label: "In Progress" };
    case "action_needed":
    case "rfe_response":  return { bg: "bg-[#fff7ed]", border: "border-[#fed7aa]",  text: "text-[#c2410c]", label: "Action Needed" };
    case "rejected":      return { bg: "bg-[#fef2f2]", border: "border-[#fecaca]",  text: "text-[#b91c1c]", label: "Rejected" };
    default:              return { bg: "bg-[#f8fafc]", border: "border-[#e2e8f0]",  text: "text-[#64748b]", label: "Draft" };
  }
}

// ── Timeline stages ───────────────────────────────────────────────────────────
const STAGES: { key: ApplicationStage; label: string }[] = [
  { key: "profile_eligibility", label: "Profile & Eligibility" },
  { key: "documentation",       label: "Documentation"         },
  { key: "lca_filing",          label: "LCA Filing"            },
  { key: "uscis_submission",    label: "USCIS Submission"       },
];

function StageItem({ label, stageKey, currentStage, completedStages }: {
  label: string; stageKey: ApplicationStage;
  currentStage?: ApplicationStage; completedStages: ApplicationStage[];
}) {
  const isDone    = completedStages.includes(stageKey);
  const isCurrent = stageKey === currentStage;
  return (
    <div className="relative flex flex-col gap-[4px] items-start">
      {isDone ? (
        <div className="absolute -left-[31px] top-[4px] bg-[#ecfdf5] border-2 border-[#10b981]
                        flex items-center justify-center rounded-full size-[20px]">
          <img src={imgCheck} alt="" className="w-[8.75px] h-[10px] object-contain" />
        </div>
      ) : isCurrent ? (
        <div className="absolute -left-[31px] top-[4px] bg-[#f0f5ff] border-2 border-[#5269f2]
                        flex items-center justify-center rounded-full size-[20px] p-[7px]">
          <div className="bg-[#3a46e5] rounded-full shrink-0 size-[6px]" />
        </div>
      ) : (
        <div className="absolute -left-[31px] top-[4px] bg-white border-2 border-[#e2e8f0] rounded-full size-[20px]" />
      )}
      <p className={`leading-[20px] text-[14px] tracking-[-0.5px] ${
        isDone || isCurrent ? "font-semibold text-[#0f172a]" : "font-medium text-[#64748b]"
      }`}>{label}</p>
      {isDone ? (
        <p className="text-[#64748b] text-[12px] leading-[16px] tracking-[-0.5px]">Completed</p>
      ) : isCurrent ? (
        <p className="text-[#3a46e5] font-medium text-[12px] leading-[16px] tracking-[-0.5px]">
          In Progress - Action Required
        </p>
      ) : (
        <p className="text-[#94a3b8] text-[12px] leading-[16px] tracking-[-0.5px]">Pending</p>
      )}
    </div>
  );
}

// ── Task row ──────────────────────────────────────────────────────────────────
function TaskRow({ task, onView, onUpload }: {
  task: Task; onView?: (docId: string) => void; onUpload?: (taskId: string) => void;
}) {
  const isComplete  = task.is_completed;
  const hasDocument = isComplete && !!task.document_name;
  return (
    <div className={`flex items-center justify-between p-[14px] sm:p-[17px] rounded-[12px] border w-full transition ${
      isComplete ? "bg-[rgba(236,253,245,0.3)] border-[#d1fae5]" : "bg-[#f8fafc] border-[#f1f5f9]"
    }`}>
      <div className="flex items-start gap-[12px] sm:gap-[16px] flex-1 min-w-0">
        <div className="shrink-0 mt-[2px]">
          {isComplete ? (
            <div className="bg-[#d1fae5] flex items-center justify-center rounded-full size-[22px] sm:size-[24px]">
              <img src={imgCheck} alt="" className="w-[10px] h-[11px] sm:w-[10.5px] sm:h-[12px] object-contain" />
            </div>
          ) : (
            <div className="rounded-[6px] border-2 border-[#cbd5e1] bg-white size-[22px] sm:size-[24px] shrink-0" />
          )}
        </div>
        <div className="flex flex-col gap-[4px] min-w-0 flex-1">
          <p className="font-semibold text-[13px] sm:text-[14px] text-[#0f172a] leading-[20px] tracking-[-0.5px]">
            {task.name}
          </p>
          {hasDocument ? (
            <div className="flex items-center gap-[8px] mt-[2px]">
              <img src={imgPdfIcon} alt="" className="w-[14px] h-[14px] object-contain shrink-0" />
              <div className="flex flex-col gap-[1px] min-w-0">
                <span className="font-medium text-[12px] text-[#0f172a] leading-[16px] tracking-[-0.5px] truncate">
                  {task.document_name}
                </span>
                <span className="text-[11px] text-[#64748b] leading-[14px] tracking-[-0.5px]">
                  {[
                    task.document_size_bytes ? fmtFileSize(task.document_size_bytes) : null,
                    task.document_uploaded_at ? `Uploaded ${fmtDate(task.document_uploaded_at)}` : "Uploaded",
                  ].filter(Boolean).join(" • ")}
                </span>
              </div>
            </div>
          ) : (
            <p className={`text-[12px] leading-[16px] tracking-[-0.5px] ${
              isComplete ? "text-[#059669] font-medium" : "text-[#94a3b8] font-normal"
            }`}>
              {isComplete ? "✓ Uploaded & Verified" : task.description ?? "Pending upload"}
            </p>
          )}
        </div>
      </div>
      <div className="shrink-0 ml-[12px] sm:ml-[16px]">
        {hasDocument && task.document_id ? (
          <button onClick={() => onView?.(task.document_id!)}
            className="bg-white border border-[#e2e8f0] h-[28px] sm:h-[30px] px-[10px] sm:px-[12px]
                       rounded-[8px] text-[#64748b] text-[12px] font-medium tracking-[-0.5px]
                       whitespace-nowrap hover:bg-[#f9fafb] transition">
            View
          </button>
        ) : !isComplete ? (
          <button onClick={() => onUpload?.(task.id)}
            className="h-[28px] sm:h-[30px] px-[10px] sm:px-[12px] rounded-[8px] text-white
                       text-[12px] font-medium tracking-[-0.5px] whitespace-nowrap transition hover:opacity-90"
            style={{ backgroundImage: "linear-gradient(168.63deg, rgb(58,70,229) 0%, rgb(157,78,221) 100%)" }}>
            Upload
          </button>
        ) : null}
      </div>
    </div>
  );
}

// ── Document preview modal ────────────────────────────────────────────────────
function DocumentPreviewModal({ docId, onClose }: { docId: string; onClose: () => void }) {
  const [blobUrl,  setBlobUrl]  = useState<string | null>(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);
  const [fileType, setFileType] = useState<"image" | "pdf" | "other">("image");
  const [fileName, setFileName] = useState("");

  useEffect(() => { document.body.style.overflow = "hidden"; return () => { document.body.style.overflow = ""; }; }, []);
  const handleKey = useCallback((e: KeyboardEvent) => { if (e.key === "Escape") onClose(); }, [onClose]);
  useEffect(() => { window.addEventListener("keydown", handleKey); return () => window.removeEventListener("keydown", handleKey); }, [handleKey]);

  useEffect(() => {
    let objectUrl: string | null = null;
    (async () => {
      try {
        const response = await documentsApi.getFile(docId);
        objectUrl = URL.createObjectURL(response.blob);
        setBlobUrl(objectUrl);
        setFileName(response.fileName);
        if (response.contentType.startsWith("image/"))   setFileType("image");
        else if (response.contentType.includes("pdf"))   setFileType("pdf");
        else                                              setFileType("other");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load file.");
      } finally { setLoading(false); }
    })();
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [docId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-[16px] sm:p-[24px]"
      style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(4px)" }} onClick={onClose}>
      <div className="relative bg-[#1e293b] rounded-[16px] overflow-hidden flex flex-col
                      w-full max-w-[90vw] sm:max-w-[720px] max-h-[90vh] shadow-2xl"
        onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-[16px] sm:px-[20px] py-[12px] sm:py-[14px]
                        border-b border-white/10 shrink-0">
          <p className="text-white text-[13px] sm:text-[14px] font-medium truncate pr-[16px]">
            {fileName || "Document Preview"}
          </p>
          <div className="flex items-center gap-[8px] shrink-0">
            {blobUrl && (
              <a href={blobUrl} download={fileName}
                className="bg-white/10 hover:bg-white/20 text-white rounded-[8px]
                           px-[8px] sm:px-[10px] py-[5px] sm:py-[6px] text-[12px] font-medium
                           transition flex items-center gap-[6px]">
                <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
                </svg>
                <span className="hidden sm:inline">Download</span>
              </a>
            )}
            <button onClick={onClose} className="bg-white/10 hover:bg-white/20 text-white rounded-[8px] p-[6px] transition">
              <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-auto flex items-center justify-center bg-[#0f172a] min-h-[250px] p-[16px] sm:p-[24px]">
          {loading && (
            <div className="flex flex-col items-center gap-[12px]">
              <svg className="w-8 h-8 animate-spin text-white/60" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <p className="text-white/40 text-[13px]">Loading preview…</p>
            </div>
          )}
          {error && (
            <div className="text-center">
              <p className="text-[#ef4444] text-[14px] font-medium mb-[6px]">Failed to load</p>
              <p className="text-white/40 text-[12px]">{error}</p>
            </div>
          )}
          {blobUrl && fileType === "image" && (
            <img src={blobUrl} alt={fileName} className="max-w-full max-h-[70vh] object-contain rounded-[8px]"
              style={{ boxShadow: "0 25px 50px -12px rgba(0,0,0,0.8)" }} />
          )}
          {blobUrl && fileType === "pdf" && (
            <iframe src={blobUrl} title={fileName} className="w-full rounded-[4px]"
              style={{ height: "65vh", border: "none", background: "white" }} />
          )}
          {blobUrl && fileType === "other" && (
            <div className="text-center py-[32px]">
              <p className="text-white/60 text-[14px] mb-[16px]">This file type cannot be previewed.</p>
              <a href={blobUrl} download={fileName}
                className="bg-[#3a46e5] hover:bg-[#2f3ad4] text-white text-[14px] font-medium
                           px-[20px] py-[10px] rounded-[10px] transition">
                Download to view
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ApplicationDetail() {
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: app,   isLoading: appLoading,  error: appError } = useApplication(id);
  const { data: tasks, isLoading: tasksLoading }                  = useApplicationTasks(id);

  const [submitting,   setSubmitting]   = useState(false);
  const [previewDocId, setPreviewDocId] = useState<string | null>(null);

  const badge          = getStatusBadge(app?.status ?? "draft");
  const progressPct    = app?.progress_percent ?? 0;
  const tasksArr       = tasks ?? [];
  const completedCount = tasksArr.filter(t => t.is_completed).length;
  const totalCount     = tasksArr.length;

  const stageOrder      = STAGES.map(s => s.key);
  const currentIdx      = stageOrder.indexOf(app?.current_stage ?? "profile_eligibility");
  const completedStages = stageOrder.slice(0, Math.max(0, currentIdx)) as ApplicationStage[];

  function handleUpload(taskId: string) {
    navigate(`/documents/upload?application_id=${id}&task_id=${taskId}`);
  }
  async function handleSubmit() {
    setSubmitting(true);
    setTimeout(() => { setSubmitting(false); navigate("/applications/list"); }, 800);
  }
  async function handleMessageSupport() {
    try {
      const appAny   = app as unknown as Record<string, string | undefined>;
      const hrUserId = appAny.assigned_hr_id ?? appAny.created_by;
      if (!hrUserId) { navigate("/messages"); return; }
      const thread = await messageApi.createConversation({
        thread_type:     "direct",
        participant_ids: [hrUserId],
        application_id:  app!.id,
        initial_message: `Hi, I have a question about my ${app!.visa_type?.code ?? "visa"} application.`,
      });
      navigate(`/messages?thread_id=${thread.id}`);
    } catch { navigate("/messages"); }
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (appLoading || tasksLoading) {
    return (
      <div className="flex flex-col h-full">
        <PageHeader title="Application Detail" />
        <PageContent>
          <div className="flex items-center justify-center py-[64px]">
            <svg className="w-8 h-8 animate-spin text-[#3a46e5]" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        </PageContent>
      </div>
    );
  }

  if (appError || !app) {
    return (
      <div className="flex flex-col h-full">
        <PageHeader title="Application Detail" />
        <PageContent>
          <div className="flex items-center justify-center py-[64px]">
            <div className="text-center">
              <p className="text-[#ef4444] text-[16px] font-medium mb-[4px]">Failed to load application</p>
              <p className="text-[#64748b] text-[14px]">{appError ?? "Application not found"}</p>
              <button onClick={() => navigate("/applications/list")}
                className="mt-[16px] text-[#3a46e5] text-[14px] font-medium hover:underline">
                ← Back to Applications
              </button>
            </div>
          </div>
        </PageContent>
      </div>
    );
  }

  const visaTitle = app.visa_type?.name ?? "Application Detail";

  return (
    <div className="flex flex-col h-full" style={{ fontFamily: "Inter, sans-serif" }}>

      {/* ── PageHeader ── */}
      <PageHeader
        title={`${app.visa_type?.code ?? "Visa"} Application`}
        subtitle={app.sponsor_employer ?? undefined}
        showSearch={false}
      />

      <PageContent>
        <div className="flex flex-col gap-[20px] sm:gap-[24px] lg:gap-[32px]">

          {/* ── Breadcrumb ── */}
          <div className="flex items-center gap-[8px]">
            <Link to="/applications/list"
              className="text-[#64748b] text-[13px] sm:text-[14px] font-normal tracking-[-0.5px]
                         hover:text-[#0f172a] transition-colors">
              Applications
            </Link>
            <img src={imgBreadArrow} alt="" className="w-[6.25px] h-[10px] object-contain" />
            <span className="text-[#0f172a] text-[13px] sm:text-[14px] font-medium tracking-[-0.5px] truncate">
              {visaTitle}
            </span>
          </div>

          {/* ── Responsive layout: stacks on mobile, side-by-side on lg ── */}
          <div className="flex flex-col lg:flex-row gap-[20px] sm:gap-[24px] items-start w-full">

            {/* ── LEFT COLUMN ── */}
            <div className="flex flex-col gap-[20px] sm:gap-[24px] w-full lg:w-[320px] xl:w-[356px] lg:shrink-0">

              {/* Summary card */}
              <div className="bg-white border border-[#f1f5f9] rounded-[16px]
                              shadow-[0px_4px_12px_0px_rgba(0,0,0,0.02)]
                              flex flex-col gap-[16px] p-[20px] sm:p-[25px] overflow-hidden relative">
                <div className="absolute bg-[#f0f5ff] h-[128px] right-0 top-0 w-[100px]
                                rounded-bl-full opacity-50 pointer-events-none" />

                <div className="flex items-center justify-between w-full">
                  <h2 className="font-bold text-[#0f172a] text-[16px] sm:text-[18px] leading-[28px] tracking-[-0.5px]">
                    {app.visa_type?.code ?? "—"} Visa
                  </h2>
                  <span className={`${badge.bg} border ${badge.border} ${badge.text} font-bold
                                    text-[11px] sm:text-[12px] leading-[16px] tracking-[-0.5px]
                                    px-[8px] sm:px-[10px] py-[4px] sm:py-[5px] rounded-[6px] whitespace-nowrap`}>
                    {badge.label}
                  </span>
                </div>

                <p className="text-[#64748b] text-[13px] sm:text-[14px] font-normal leading-[20px] tracking-[-0.5px]">
                  {app.sponsor_employer ?? "No sponsor"}
                </p>

                <div className="bg-[#f8fafc] border border-[#f1f5f9] rounded-[12px] p-[14px] sm:p-[17px]
                                flex flex-col gap-[8px] w-full">
                  <div className="flex items-center justify-between">
                    <span className="text-[#64748b] font-medium text-[12px] leading-[16px] tracking-[-0.5px]">
                      Overall Progress
                    </span>
                    <span className="text-[#3a46e5] font-bold text-[12px] leading-[16px] tracking-[-0.5px]">
                      {progressPct}%
                    </span>
                  </div>
                  <div className="bg-[#e2e8f0] rounded-full h-[6px] w-full overflow-hidden">
                    <div className="h-[6px] rounded-full transition-all duration-500"
                      style={{
                        width: `${progressPct}%`,
                        backgroundImage: "linear-gradient(177.18deg, rgb(58,70,229) 0%, rgb(157,78,221) 100%)",
                      }} />
                  </div>
                </div>

                <div className="flex items-center justify-between w-full">
                  <span className="text-[#64748b] text-[12px] font-normal leading-[16px] tracking-[-0.5px]">
                    Started: {fmtDate(app.start_date ?? app.created_at)}
                  </span>
                  <span className="text-[#64748b] text-[12px] font-normal leading-[16px] tracking-[-0.5px]">
                    Due: {fmtDate(app.due_date)}
                  </span>
                </div>
              </div>

              {/* Timeline card */}
              <div className="bg-white border border-[#f1f5f9] rounded-[16px]
                              drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)]
                              flex flex-col gap-[20px] sm:gap-[24px] p-[20px] sm:p-[25px] w-full">
                <h3 className="font-semibold text-[#0f172a] text-[15px] sm:text-[16px] leading-[24px] tracking-[-0.5px]">
                  Application Timeline
                </h3>
                <div className="border-l-2 border-[#f1f5f9] flex flex-col gap-[28px] sm:gap-[32px] pl-[24px] sm:pl-[26px]">
                  {STAGES.map(stage => (
                    <StageItem
                      key={stage.key} label={stage.label} stageKey={stage.key}
                      currentStage={app.current_stage} completedStages={completedStages}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* ── RIGHT COLUMN ── */}
            <div className="flex flex-col gap-[20px] sm:gap-[24px] flex-1 min-w-0 w-full">

              {/* Application Actions */}
              <div className="bg-white border border-[#f1f5f9] rounded-[16px]
                              drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)]
                              flex flex-col gap-[16px] p-[20px] sm:p-[25px] w-full">
                <h3 className="font-semibold text-[#0f172a] text-[16px] sm:text-[18px] leading-[28px] tracking-[-0.5px]">
                  Application Actions
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-[12px] sm:gap-[16px]">
                  <button onClick={() => navigate(`/applications/${app.id}/book-consultation`)}
                    className="border border-[#e2e8f0] rounded-[12px] p-[14px] sm:p-[16px]
                               flex flex-col items-start gap-[6px] sm:gap-[8px] hover:bg-[#f8fafc] transition text-left">
                    <span className="font-semibold text-[#0f172a] text-[13px] sm:text-[14px] leading-[20px] tracking-[-0.5px]">
                      Book Consultation
                    </span>
                    <span className="text-[11px] sm:text-[12px] text-[#64748b] leading-[16px] tracking-[-0.5px]">
                      Schedule consultation with an immigration attorney.
                    </span>
                  </button>
                  <button onClick={() => navigate(`/applications/${app.id}/payments`)}
                    className="border border-[#e2e8f0] rounded-[12px] p-[14px] sm:p-[16px]
                               flex flex-col items-start gap-[6px] sm:gap-[8px] hover:bg-[#f8fafc] transition text-left">
                    <span className="font-semibold text-[#0f172a] text-[13px] sm:text-[14px] leading-[20px] tracking-[-0.5px]">
                      Payments & Billing
                    </span>
                    <span className="text-[11px] sm:text-[12px] text-[#64748b] leading-[16px] tracking-[-0.5px]">
                      Pay fees and manage invoices.
                    </span>
                  </button>
                </div>
              </div>

              {/* Required Tasks */}
              <div className="bg-white border border-[#f1f5f9] rounded-[16px]
                              drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)]
                              flex flex-col gap-[20px] sm:gap-[24px] p-[20px] sm:p-[25px] w-full">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-[#0f172a] text-[16px] sm:text-[18px] leading-[28px] tracking-[-0.5px]">
                    Required Tasks
                  </h3>
                  <span className="bg-[#f8fafc] border border-[#e2e8f0] text-[#64748b] font-medium
                                   text-[11px] sm:text-[12px] leading-[16px] tracking-[-0.5px]
                                   px-[8px] sm:px-[10px] py-[4px] sm:py-[5px] rounded-[6px] whitespace-nowrap">
                    {completedCount} of {totalCount} Completed
                  </span>
                </div>
                <div className="flex flex-col gap-[10px] sm:gap-[12px]">
                  {tasksArr.length > 0 ? (
                    tasksArr.map(task => (
                      <TaskRow key={task.id} task={task} onView={setPreviewDocId} onUpload={handleUpload} />
                    ))
                  ) : (
                    <p className="text-[#64748b] text-[14px] text-center py-[16px]">
                      No tasks found for this application.
                    </p>
                  )}
                </div>
              </div>

              {/* Footer actions */}
              <div className="border-t border-[#e2e8f0] flex flex-col sm:flex-row items-stretch sm:items-center
                              justify-between gap-[12px] pt-[20px] sm:pt-[25px]">
                <button onClick={handleMessageSupport}
                  className="bg-white border border-[#e2e8f0] flex items-center justify-center sm:justify-start
                             gap-[8px] h-[42px] px-[20px] sm:px-[25px] rounded-[12px] text-[#334155]
                             text-[13px] sm:text-[14px] font-medium tracking-[-0.5px] leading-[20px]
                             hover:bg-[#f9fafb] transition">
                  <img src={imgMsgIcon} alt="" className="w-[14px] h-[14px] object-contain shrink-0" />
                  Message Support
                </button>
                <div className="flex items-center gap-[10px] sm:gap-[12px]">
                  <button onClick={() => navigate("/applications")}
                    className="bg-[#f1f5f9] flex items-center justify-center h-[40px] flex-1 sm:flex-none
                               px-[20px] sm:px-[24px] rounded-[12px] text-[#334155] text-[13px] sm:text-[14px]
                               font-medium tracking-[-0.5px] leading-[20px] hover:bg-[#e2e8f0] transition">
                    Save Draft
                  </button>
                  <button onClick={handleSubmit} disabled={submitting}
                    className="flex items-center justify-center gap-[8px] h-[40px] flex-1 sm:flex-none
                               px-[20px] sm:px-[24px] rounded-[12px] text-white text-[13px] sm:text-[14px]
                               font-medium tracking-[-0.5px] leading-[20px] opacity-75
                               drop-shadow-[0px_1px_1px_rgba(0,0,0,0.05)] hover:opacity-100
                               transition disabled:opacity-40"
                    style={{ backgroundImage: "linear-gradient(168.63deg, rgb(58,70,229) 0%, rgb(157,78,221) 100%)" }}>
                    {submitting ? "Submitting…" : "Submit when ready"}
                    <img src={imgArrowRight} alt="" className="size-[14px] object-contain shrink-0" />
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>
      </PageContent>

      {previewDocId && (
        <DocumentPreviewModal docId={previewDocId} onClose={() => setPreviewDocId(null)} />
      )}
    </div>
  );
}