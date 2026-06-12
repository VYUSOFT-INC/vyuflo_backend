// src/pages/employee/DocumentUpload.tsx
import documentsApi        from "../../api/employee/documents.api";
import { useRef, useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useApplication, useApplicationTasks } from "../../hooks/employee/useApplications";

// ── Assets ────────────────────────────────────────────────────────────────────
import imgProgressIcon from "../../assets/icons/docup-progress-icon.svg";
import imgIdentityIcon from "../../assets/icons/docup-identity-icon.svg";
import imgPdfIcon      from "../../assets/icons/docup-pdf-icon.svg";
import imgEyeIcon      from "../../assets/icons/eye-icon.svg";
import imgTrashIcon    from "../../assets/icons/appdetail-trash-icon.svg";
import imgImgIcon      from "../../assets/icons/docup-img-icon.svg";
import imgUploadIcon   from "../../assets/icons/docup-upload-icon.svg";

// ── Document category map — derived from DOCUMENT_TYPES_SEED ─────────────────
const DOCUMENT_CATEGORY_MAP: Record<string, string> = {
  "Passport Copy":                                   "identity",
  "Birth Certificate":                               "identity",
  "Two Passport Photos":                             "identity",
  "Copy of Current Visa":                            "identity",
  "Current Immigration Status Evidence":             "identity",
  "Offer Letter":                                    "employment",
  "Resume / CV":                                     "employment",
  "Pay Stubs (Last 3 Months)":                       "employment",
  "Proof of Employment Abroad":                      "employment",
  "Employment Verification Letter":                  "employment",
  "Organizational Chart":                            "employment",
  "Contracts or Itinerary":                          "employment",
  "Employer Attestation":                            "employment",
  "Enrollment Verification":                         "employment",
  "Educational Transcripts":                         "education",
  "STEM Degree Transcript":                          "education",
  "Acceptance Letter":                               "education",
  "Professional License (if applicable)":            "education",
  "Previous I-797":                                  "legal",
  "Current I-797 Approval Notice":                   "legal",
  "Form I-20":                                       "legal",
  "Form I-20 (OPT Recommendation)":                  "legal",
  "Form I-20 (Updated)":                             "legal",
  "Form I-20 (CPT Authorization)":                   "legal",
  "I-983 Training Plan":                             "legal",
  "EAD Application (Form I-765)":                    "legal",
  "EAD Card":                                        "legal",
  "Form DS-2019":                                    "legal",
  "SEVIS Fee Receipt":                               "legal",
  "Form I-485":                                      "legal",
  "Medical Examination (Form I-693)":                "legal",
  "Affidavit of Support (Form I-864)":               "legal",
  "PERM Labor Certification":                        "legal",
  "Form I-140 Supporting Documents":                 "legal",
  "National Interest Waiver Justification Letter":   "legal",
  "Financial Support Evidence":                      "personal",
  "Bank Statements (Last 3 Months)":                 "personal",
  "Travel Itinerary":                                "personal",
  "Ties to Home Country Evidence":                   "personal",
  "Invitation Letter (if applicable)":               "personal",
  "Awards and Recognition Evidence":                 "other",
  "Published Work or Media Coverage":                "other",
  "Expert Reference Letters":                        "other",
  "Proof of Specialized Knowledge":                  "other",
  "Investment Evidence":                             "other",
  "Business Plan":                                   "other",
  "Source of Funds Documentation":                   "other",
  "Company Registration Documents":                  "other",
  "Company Financial Statements":                    "other",
  "Portfolio or Showreel":                           "other",
  "Critical Role Evidence":                          "other",
  "Program Sponsor Letter":                          "other",
  "Passport Photos":                                 "other",
};

// ── Types ─────────────────────────────────────────────────────────────────────
type DocStatus = "uploaded" | "pending_review" | "required" | "verified";

interface DocRow {
  id:          string;
  title:       string;
  description: string;
  status:      DocStatus;
  file?: {
    name: string;
    size: string;
    date: string;
    note?: string;
    type: "pdf" | "img";
  };
}

// ── Status badge ──────────────────────────────────────────────────────────────
function getStatusBadge(status: DocStatus) {
  switch (status) {
    case "uploaded":
    case "verified":
      return { bg: "bg-[#d1fae5]", border: "border border-[#a7f3d0]", text: "text-[#047857]", label: "Uploaded" };
    case "pending_review":
      return { bg: "bg-[#fef3c7]", border: "border border-[#fde68a]", text: "text-[#b45309]", label: "Pending Review" };
    default:
      return { bg: "bg-[#f3f4f6]", border: "border border-[#e5e7eb]", text: "text-[#4b5563]", label: "Required" };
  }
}

// ── Upload dropzone ───────────────────────────────────────────────────────────
function UploadZone({ onFile }: { onFile: (file: File) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => {
        e.preventDefault();
        setDragging(false);
        if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);
      }}
      className={`border-2 border-dashed rounded-[12px] flex flex-col gap-[4px] items-center
                  p-[20px] sm:p-[26px] cursor-pointer transition w-full ${
        dragging
          ? "border-[#2563eb] bg-[#eff6ff]"
          : "border-[#d1d5db] bg-white hover:border-[#2563eb] hover:bg-[#f9fafb]"
      }`}
    >
      <div className="bg-[#f3f4f6] rounded-full flex items-center justify-center size-[40px] shrink-0 mb-[4px]">
        <img src={imgUploadIcon} alt="" className="w-[22.5px] h-[18px] object-contain" />
      </div>
      <p className="text-[#111827] text-[13px] sm:text-[14px] font-medium leading-[20px] text-center">
        Click to upload or drag and drop
      </p>
      <p className="text-[#6b7280] text-[11px] sm:text-[12px] font-normal leading-[16px] text-center">
        PDF, JPG, PNG (max. 10MB)
      </p>
      <input ref={inputRef} type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden"
        onChange={e => { if (e.target.files?.[0]) onFile(e.target.files[0]); }} />
    </div>
  );
}

// ── Doc row item ──────────────────────────────────────────────────────────────
function DocRowItem({
  doc,
  onUpload,
  onDelete,
  uploading,
}: {
  doc:      DocRow;
  onUpload: (id: string, file: File) => void;
  onDelete: (id: string) => void;
  uploading: string | null;
}) {
  const badge       = getStatusBadge(doc.status);
  const isPending   = doc.status === "pending_review";
  const isUploading = uploading === doc.id;
  const fileIcon    = doc.file?.type === "img" ? imgImgIcon : imgPdfIcon;

  return (
    // Responsive: stack vertically on mobile, side-by-side on md+
    <div className="flex flex-col md:flex-row md:items-start gap-[16px] md:gap-[24px] p-[16px] sm:p-[24px] w-full">

      {/* Left: title + description — full width on mobile, fixed on desktop */}
      <div className="flex flex-col gap-[6px] md:shrink-0 md:w-[280px] lg:w-[303px]">
        <div className="flex gap-[10px] items-center flex-wrap">
          <span className="text-[#111827] text-[15px] sm:text-[16px] font-semibold leading-[24px]">
            {doc.title}
          </span>
          <span className={`${badge.bg} ${badge.border} ${badge.text} px-[10px] py-[4px]
                            rounded-full text-[11px] sm:text-[12px] font-medium leading-[16px] whitespace-nowrap shrink-0`}>
            {badge.label}
          </span>
        </div>
        <p className="text-[#6b7280] text-[13px] sm:text-[14px] font-normal leading-[20px]">
          {doc.description}
        </p>
      </div>

      {/* Right: spinner | file row | upload zone — full width always */}
      <div className="flex-1 min-w-0 w-full">
        {isUploading ? (
          <div className="flex items-center justify-center h-[72px] rounded-[12px] border border-[#e5e7eb] bg-[#f9fafb]">
            <svg className="w-5 h-5 animate-spin text-[#2563eb]" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="ml-[8px] text-[#6b7280] text-[13px]">Uploading…</span>
          </div>
        ) : doc.file ? (
          <div className={`flex items-center justify-between p-[12px] sm:p-[13px] rounded-[12px] border ${
            isPending ? "bg-[rgba(255,251,235,0.5)] border-[#fde68a]" : "bg-[#f9fafb] border-[#e5e7eb]"
          }`}>
            <div className="flex gap-[10px] sm:gap-[12px] items-center min-w-0 flex-1">
              <img src={fileIcon} alt="" className="size-[24px] object-contain shrink-0" />
              <div className="flex flex-col min-w-0">
                <span className="text-[#111827] text-[13px] sm:text-[14px] font-medium leading-[20px] truncate">
                  {doc.file.name}
                </span>
                {doc.file.note ? (
                  <span className="text-[#d97706] text-[11px] sm:text-[12px] font-normal leading-[16px]">
                    {doc.file.note}
                  </span>
                ) : (
                  <span className="text-[#6b7280] text-[11px] sm:text-[12px] font-normal leading-[16px]">
                    {doc.file.size}{doc.file.size && doc.file.date ? " • " : ""}{doc.file.date}
                  </span>
                )}
              </div>
            </div>
            <div className="flex gap-[4px] sm:gap-[8px] items-center pl-[8px] sm:pl-[16px] shrink-0">
              <button type="button"
                className="flex items-center justify-center p-[6px] sm:px-[8px] sm:py-[6px] rounded-[8px] hover:bg-[#f3f4f6] transition">
                <img src={imgEyeIcon} alt="View" className="w-[18px] h-[16px] object-contain" />
              </button>
              {!isPending && (
                <button type="button" onClick={() => onDelete(doc.id)}
                  className="flex items-center justify-center p-[6px] sm:px-[8px] sm:py-[6px] rounded-[8px] hover:bg-[#fee2e2] transition">
                  <img src={imgTrashIcon} alt="Delete" className="w-[14px] h-[16px] object-contain" />
                </button>
              )}
            </div>
          </div>
        ) : (
          <UploadZone onFile={file => onUpload(doc.id, file)} />
        )}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function DocumentUpload() {
  const navigate       = useNavigate();
  const [searchParams] = useSearchParams();

  const applicationId = searchParams.get("application_id") ?? undefined;

  const { data: app, isLoading: appLoading } = useApplication(applicationId);
  const visaName = app?.visa_type?.name ?? "visa";

  const { data: tasks, isLoading: tasksLoading } = useApplicationTasks(applicationId);

  const [docs,       setDocs]       = useState<DocRow[]>([]);
  const [uploading,  setUploading]  = useState<string | null>(null);
  const [saving,     setSaving]     = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!tasks) return;
    setDocs(tasks.map(task => ({
      id:          task.id,
      title:       task.name,
      description: task.description ?? "",
      status:      task.is_completed ? "uploaded" : "required",
      file:        task.document_name ? {
        name: task.document_name,
        size: task.document_size_bytes
          ? `${(task.document_size_bytes / 1024 / 1024).toFixed(1)} MB`
          : "",
        date: task.document_uploaded_at
          ? `Uploaded ${new Date(task.document_uploaded_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`
          : "",
        type: "pdf" as const,
      } : undefined,
    })));
  }, [tasks]);

  const uploaded    = docs.filter(d => d.file).length;
  const total       = docs.length;
  const progressPct = total > 0 ? Math.round((uploaded / total) * 100) : 0;

  async function handleUpload(taskId: string, file: File) {
    if (!applicationId) return;
    setUploading(taskId);
    try {
      const task     = tasks?.find(t => t.id === taskId);
      const taskName = task?.name ?? "";
      const category = DOCUMENT_CATEGORY_MAP[taskName] ?? "other";
      await documentsApi.upload({
        application_id: applicationId,
        document_type:  taskName || taskId,
        category,
        file,
      });
      const fileEntry = {
        name: file.name,
        size: `${(file.size / 1024 / 1024).toFixed(1)} MB`,
        date: "Just now",
        type: (file.type.startsWith("image/") ? "img" : "pdf") as "img" | "pdf",
      };
      setDocs(prev => prev.map(d =>
        d.id === taskId ? { ...d, status: "uploaded" as DocStatus, file: fileEntry } : d
      ));
    } catch (e) {
      console.error("Upload failed", e);
    } finally {
      setUploading(null);
    }
  }

  function handleDelete(taskId: string) {
    setDocs(prev => prev.map(d =>
      d.id === taskId ? { ...d, status: "required" as DocStatus, file: undefined } : d
    ));
  }

  function handleSaveDraft() {
    setSaving(true);
    const dest = applicationId ? `/applications/${applicationId}` : "/applications/list";
    setTimeout(() => { setSaving(false); navigate(dest); }, 600);
  }

  function handleSubmit() {
    setSubmitting(true);
    const dest = applicationId ? `/applications/${applicationId}` : "/applications/list";
    setTimeout(() => { setSubmitting(false); navigate(dest); }, 600);
  }

  if (appLoading || tasksLoading) {
    return (
      <div className="flex items-center justify-center py-[64px]">
        <svg className="w-8 h-8 animate-spin text-[#2563eb]" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  return (
    // ── Full page: outer constrains height, inner scrolls ────────────────────
    // Matches Dashboard / ApplicationsList pattern exactly
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden" style={{ fontFamily: "Inter, sans-serif" }}>

      {/* Scrollable content area — footer is fixed so give bottom padding */}
      <main className="flex-1 overflow-y-auto px-[16px] sm:px-[32px] py-[24px] sm:py-[32px]">
        <div className="flex flex-col gap-[24px] sm:gap-[32px] pb-[80px] max-w-[1200px] mx-auto">

      {/* ── Page Header ── */}
      <div className="flex flex-col gap-[6px] sm:gap-[8px]">
        <h1 className="text-[#111827] text-[22px] sm:text-[28px] lg:text-[30px] font-bold leading-[32px] sm:leading-[36px] tracking-[-0.5px] sm:tracking-[-0.75px]">
          Upload Your Documents
        </h1>
        <p className="text-[#4b5563] text-[14px] sm:text-[16px] lg:text-[18px] font-normal leading-[24px] sm:leading-[28px]">
          Please provide the required documentation for your{" "}
          <span className="font-semibold text-[#111827]">{visaName}</span>{" "}
          application. Ensure all files are clear and legible.
        </p>
      </div>

      {/* ── Progress Card ── */}
      <div className="bg-white border border-[#f3f4f6] rounded-[16px]
                      shadow-[0px_4px_6px_-1px_rgba(0,0,0,0.05),0px_2px_4px_-1px_rgba(0,0,0,0.03)]
                      p-[20px] sm:p-[28px] lg:p-[33px] flex flex-col gap-[12px] w-full">
        <div className="flex items-start sm:items-center justify-between gap-[12px] pb-[8px] sm:pb-[12px]">
          <div className="flex flex-col gap-[4px]">
            <div className="flex gap-[8px] items-center">
              <img src={imgProgressIcon} alt="" className="w-[20px] sm:w-[22.5px] h-[18px] sm:h-[20px] object-contain" />
              <span className="text-[#111827] text-[16px] sm:text-[18px] lg:text-[20px] font-bold leading-[28px]">
                Application Progress
              </span>
            </div>
            <p className="text-[#6b7280] text-[12px] sm:text-[14px] font-normal leading-[20px]">
              {uploaded} of {total} required documents uploaded
            </p>
          </div>
          <div className="bg-[rgba(37,99,235,0.1)] flex gap-[6px] sm:gap-[8px] items-center
                          px-[10px] sm:px-[16px] py-[6px] sm:py-[8px] rounded-full shrink-0">
            <div className="bg-[#2563eb] rounded-full size-[7px] sm:size-[8px] shrink-0" />
            <span className="text-[#2563eb] text-[12px] sm:text-[14px] font-semibold leading-[20px] whitespace-nowrap">
              In Progress
            </span>
          </div>
        </div>
        <div className="bg-[#f3f4f6] h-[12px] sm:h-[16px] rounded-full w-full overflow-hidden">
          <div className="h-full rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%`, backgroundImage: "linear-gradient(to right, #2563eb, #7c3aed)" }} />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[#4f46e5] text-[13px] sm:text-[14px] font-medium leading-[20px]">{progressPct}% Complete</span>
          <span className="text-[#6b7280] text-[13px] sm:text-[14px] font-medium leading-[20px]">100%</span>
        </div>
      </div>

      {/* ── Document rows ── */}
      {docs.length === 0 ? (
        <div className="bg-white border border-[#f3f4f6] rounded-[16px]
                        shadow-[0px_4px_6px_-1px_rgba(0,0,0,0.05)] p-[48px] text-center">
          <p className="text-[#6b7280] text-[14px]">No documents required for this application.</p>
        </div>
      ) : (
        <div className="bg-white border border-[#f3f4f6] rounded-[16px]
                        shadow-[0px_4px_6px_-1px_rgba(0,0,0,0.05),0px_2px_4px_-1px_rgba(0,0,0,0.03)]
                        overflow-hidden w-full">
          {/* Section header */}
          <div className="bg-[rgba(249,250,251,0.8)] border-b border-[#f3f4f6]
                          flex gap-[10px] sm:gap-[12px] items-center px-[16px] sm:px-[24px] py-[14px] sm:py-[16px]">
            <div className="bg-[#dbeafe] rounded-[8px] flex items-center justify-center size-[32px] shrink-0">
              <img src={imgIdentityIcon} alt="" className="w-[18px] h-[16px] object-contain" />
            </div>
            <span className="text-[#111827] text-[15px] sm:text-[18px] font-semibold leading-[28px]">
              Required Documents — {app?.visa_type?.code ?? ""}
            </span>
            <span className="ml-auto text-[#6b7280] text-[12px] sm:text-[13px] whitespace-nowrap">
              {uploaded} / {total} uploaded
            </span>
          </div>
          {/* Rows — divider between each */}
          <div className="flex flex-col divide-y divide-[#f3f4f6]">
            {docs.map(doc => (
              <DocRowItem
                key={doc.id}
                doc={doc}
                onUpload={handleUpload}
                onDelete={handleDelete}
                uploading={uploading}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Sticky Footer ── */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-[#e5e7eb]
                      shadow-[0px_-4px_6px_-1px_rgba(0,0,0,0.05)]
                      flex items-center justify-between
                      px-[16px] sm:px-[32px] lg:px-[48px] py-[14px] sm:py-[16px]
                      z-20">
        <p className="text-[#4b5563] text-[12px] sm:text-[14px] font-normal leading-[20px] hidden sm:block">
          Please ensure all documents are accurate before submitting.
        </p>
        <div className="flex gap-[10px] sm:gap-[16px] items-center w-full sm:w-auto justify-between sm:justify-end">
          <button type="button" onClick={handleSaveDraft} disabled={saving}
            className="border border-[#d1d5db] flex items-center justify-center
                       px-[16px] sm:px-[25px] py-[10px] sm:py-[11px]
                       rounded-[8px] text-[#374151] text-[14px] sm:text-[16px] font-medium leading-[24px]
                       hover:bg-[#f9fafb] transition disabled:opacity-60 whitespace-nowrap">
            {saving ? "Saving…" : "Save Draft"}
          </button>
          <button type="button" onClick={handleSubmit} disabled={submitting}
            className="flex items-center justify-center
                       px-[20px] sm:px-[32px] py-[10px]
                       rounded-[8px] text-white text-[14px] sm:text-[16px] font-medium leading-[24px]
                       shadow-[0px_4px_6px_-1px_rgba(0,0,0,0.1)] hover:opacity-90 transition
                       disabled:opacity-60 whitespace-nowrap"
            style={{ backgroundImage: "linear-gradient(to right, #2563eb, #7c3aed)" }}>
            {submitting ? "Submitting…" : "Submit for Review"}
          </button>
        </div>
      </div>
        </div>
      </main>
    </div>
  );
}