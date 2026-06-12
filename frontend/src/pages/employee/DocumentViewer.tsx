// src/pages/employee/DocumentViewer.tsx
import { useState, useEffect }         from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useDocument }                  from "../../hooks/employee/useDocuments";
import { useOCR }                       from "../../hooks/employee/useOCR";
import documentsApi                     from "../../api/employee/documents.api";
// import axiosInstance                    from "../../api/axios";

// ── Helpers ───────────────────────────────────────────────────────────────────
function confBadge(score: number) {
  if (score >= 90) return { bg: "bg-[#dcfce7]", text: "text-[#16a34a]" };
  if (score >= 75) return { bg: "bg-[#fef9c3]", text: "text-[#ca8a04]" };
  return               { bg: "bg-[#fee2e2]",    text: "text-[#dc2626]" };
}

function PageStatus({ status }: { status: string }) {
  if (status === "processed" || status === "confirmed")
    return <span className="text-[#16a34a] text-[10px] font-semibold">Processed</span>;
  if (status === "review_needed")
    return <span className="text-[#d97706] text-[10px] font-semibold">Review</span>;
  return <span className="text-[#6366f1] text-[10px] font-semibold">Processing</span>;
}

// ── Spinner ───────────────────────────────────────────────────────────────────
function Spinner({ color = "text-[#3a46e5]" }: { color?: string }) {
  return (
    <svg className={`w-8 h-8 animate-spin ${color}`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
export default function DocumentViewer() {
  const navigate       = useNavigate();
  const [searchParams] = useSearchParams();
  const docId          = searchParams.get("doc_id")         ?? undefined;
  const returnAppId    = searchParams.get("application_id") ?? undefined;

  const { data: doc, isLoading: docLoading, error: docError } = useDocument(docId);

  const [fileUrl,     setFileUrl]     = useState<string | null>(null);
  const [fileName,    setFileName]    = useState<string>("");
  const [fileBlob,    setFileBlob]    = useState<Blob | null>(null);
  const [zoom,        setZoom]        = useState(100);
  const [rotation,    setRotation]    = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [rightOpen,   setRightOpen]   = useState(true);

  // Mobile tab: "pages" | "viewer" | "data"
  const [mobileTab, setMobileTab] = useState<"pages" | "viewer" | "data">("viewer");

  const totalPages = doc?.total_pages ?? 1;
  const isPdf      = doc?.file_type === "pdf" || fileName.endsWith(".pdf");

  const {
    fields, avgConfidence, source,
    isLoading: ocrLoading, error: ocrError,
    loadFields, submitFields, confirmField,
    saveEdit, startEdit, cancelEdit, updateEditValue,
  } = useOCR(docId);

  useEffect(() => {
    if (!docId) return;
    let objectUrl: string;
    documentsApi.getFile(docId)
      .then(({ blob, fileName: name }) => {
        objectUrl = URL.createObjectURL(blob);
        setFileUrl(objectUrl);
        setFileName(name);
        setFileBlob(blob);
      })
      .catch(err => console.error("Failed to load document file:", err));
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [docId]);

  useEffect(() => {
    if (fileBlob && fileName && fields.length === 0 && !ocrLoading) {
      void loadFields(fileBlob, fileName);
    }
  }, [fileBlob, fileName]); // eslint-disable-line react-hooks/exhaustive-deps

  // async function handleNextDocument() {
  //   if (!returnAppId) { navigate("/documents"); return; }
  //   try {
  //     const res  = await axiosInstance.get(`/documents?application_id=${returnAppId}`);
  //     const docs = (res.data?.items ?? res.data ?? []) as { id: string }[];
  //     const idx  = docs.findIndex(d => d.id === docId);
  //     const next = docs[idx + 1];
  //     if (next) navigate(`/documents/viewer?doc_id=${next.id}&application_id=${returnAppId}`);
  //     else      navigate(`/applications/${returnAppId}`);
  //   } catch {
  //     navigate(returnAppId ? `/applications/${returnAppId}` : "/documents");
  //   }
  // }

  function exportData() {
    const rows = fields.map(f =>
      `"${f.field_name}","${f.extracted_value}",${f.confidence_score},${f.is_confirmed}`
    );
    const csv  = ["Field Name,Extracted Value,Confidence,Confirmed", ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `${doc?.name ?? "document"}_data.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  function handleDownload() {
    if (!fileUrl || !doc) return;
    const a = document.createElement("a");
    a.href = fileUrl; a.download = doc.name; a.click();
  }

  const confirmedCount = fields.filter(f => f.is_confirmed).length;
  const reviewCount    = fields.filter(f => f.needs_review && !f.is_confirmed).length;

  // ── Loading / Error ────────────────────────────────────────────────────────
  if (docLoading) {
    return <div className="flex items-center justify-center h-full py-[64px]"><Spinner /></div>;
  }
  if (docError || !doc) {
    return (
      <div className="flex items-center justify-center h-full py-[64px]">
        <div className="text-center">
          <p className="text-[#ef4444] text-[15px] font-medium mb-[4px]">Document not found</p>
          <p className="text-[#64748b] text-[13px] mb-[12px]">{docError ?? "Check the document ID"}</p>
          <button onClick={() => navigate("/documents")} className="text-[#3a46e5] text-[13px] font-medium hover:underline">
            ← Back to Document Hub
          </button>
        </div>
      </div>
    );
  }

  // ── Reusable panel contents ────────────────────────────────────────────────

  // Pages panel
  const PagesPanel = () => (
    <div className="flex flex-col h-full overflow-hidden bg-[#f8fafc]">

      {/* Header */}
      <div className="px-[16px] pt-[14px] pb-[12px] bg-white border-b border-[#f1f5f9] shrink-0">
        <p className="text-[#0f172a] text-[14px] font-bold">Document Pages</p>
        <p className="text-[#94a3b8] text-[11px] mt-[1px]">{totalPages} {totalPages === 1 ? "page" : "pages"}</p>
      </div>

      {/* Page grid */}
      <div className="flex-1 overflow-y-auto p-[16px]">
        <div className={totalPages === 1 ? "flex justify-center" : "grid grid-cols-2 gap-[12px]"}>
          {Array.from({ length: totalPages > 0 ? totalPages : 1 }).map((_, i) => {
            const pageNum  = i + 1;
            const isActive = currentPage === pageNum;
            const status   = i === 0 ? "processed" : i === 2 ? "processing" : "processed";
            return (
              <div key={pageNum} onClick={() => { setCurrentPage(pageNum); setMobileTab("viewer"); }}
                className={`cursor-pointer rounded-[10px] overflow-hidden border-2 transition-all bg-white shadow-sm w-full max-w-[220px] ${
                  isActive
                    ? "border-[#3a46e5] shadow-[0_0_0_3px_rgba(58,70,229,0.12)]"
                    : "border-[#e5e7eb] hover:border-[#c7d2fe]"
                }`}>
                {/* Thumbnail */}
                <div className="bg-[#f1f5f9] relative overflow-hidden" style={{ paddingTop: "70%" }}>
                  <div className="absolute inset-0 flex items-center justify-center">
                    {fileUrl && !isPdf ? (
                      <img src={fileUrl} alt={`Page ${pageNum}`}
                        className="w-full h-full object-cover"
                        style={{ transform: `rotate(${rotation}deg)` }} />
                    ) : (
                      <div className="flex flex-col items-center gap-[6px]">
                        <svg width="32" height="40" viewBox="0 0 28 34" fill="none">
                          <rect width="28" height="34" rx="4" fill="#fef2f2"/>
                          <path d="M6 4h12l6 6v20a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2z" fill="#fee2e2"/>
                          <path d="M16 4l6 6h-6V4z" fill="#fca5a5"/>
                          <text x="5" y="24" fontSize="5" fill="#ef4444" fontWeight="bold">PDF</text>
                        </svg>
                      </div>
                    )}
                  </div>
                  {/* Active indicator */}
                  {isActive && (
                    <div className="absolute top-[6px] left-[6px] bg-[#3a46e5] rounded-full w-[18px] h-[18px] flex items-center justify-center shadow-sm">
                      <svg width="9" height="9" viewBox="0 0 24 24" fill="none">
                        <path d="M20 6L9 17l-5-5" stroke="white" strokeWidth="3" strokeLinecap="round"/>
                      </svg>
                    </div>
                  )}
                </div>
                {/* Label */}
                <div className="px-[8px] py-[6px] flex items-center justify-between bg-white border-t border-[#f1f5f9]">
                  <span className="text-[#374151] text-[11px] font-medium">Page {pageNum}</span>
                  <PageStatus status={status} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  // Viewer panel
  const ViewerPanel = () => (
    <div className="flex-1 min-w-0 bg-[#e8ecf0] flex flex-col overflow-hidden relative h-full">
      <div className="absolute top-[12px] right-[14px] z-10 bg-white/90 backdrop-blur-sm border border-[#e5e7eb] rounded-[6px] px-[8px] py-[3px] text-[11px] text-[#64748b] font-medium shadow-sm">
        Page {currentPage} of {totalPages}
      </div>
      <div className="flex-1 overflow-auto flex items-start justify-center p-[16px] sm:p-[28px] pt-[24px]">
        {!fileUrl && !ocrLoading && fields.length === 0 && (
          <div className="flex flex-col items-center gap-[12px] pt-[80px]">
            <Spinner /><p className="text-[#64748b] text-[13px]">Loading document…</p>
          </div>
        )}
        {ocrLoading && fields.length === 0 && (
          <div className="flex flex-col items-center gap-[12px] pt-[80px]">
            <Spinner /><p className="text-[#64748b] text-[13px]">Extracting data from document…</p>
          </div>
        )}
        {fields.length > 0 && (
          <div className="bg-white shadow-[0_8px_32px_rgba(0,0,0,0.12)] rounded-[8px] w-full max-w-[1000px] p-[16px] sm:p-[32px] flex flex-col gap-[20px] sm:gap-[24px] transition-transform duration-200 origin-top"
            style={{ transform: `scale(${zoom / 100})` }}>
            <div className="flex flex-col gap-[2px]">
              <h2 className="text-[#111827] text-[20px] sm:text-[28px] font-bold leading-tight tracking-[-0.5px]">
                {doc.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ").toUpperCase()}
              </h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-[16px] gap-y-[16px] sm:gap-y-[20px]">
              {fields.map(field => {
                const isFullWidth = field.field_name.toLowerCase().includes("address") ||
                  field.field_name.toLowerCase().includes("employer") ||
                  field.field_name.toLowerCase().includes("issuing authority") ||
                  field.field_name.toLowerCase().includes("mrz");
                const borderColor = field.is_confirmed ? "#22c55e" : field.needs_review ? "#f59e0b" : "#d1d5db";
                const bgColor     = field.is_confirmed ? "rgba(240,253,244,0.5)" : field.needs_review ? "rgba(255,251,235,0.5)" : "white";
                return (
                  <div key={field.id} className={`flex flex-col gap-[4px] ${isFullWidth ? "sm:col-span-2" : ""}`}>
                    <label className="text-[#64748b] text-[11px] font-medium leading-[14px] tracking-[0.2px]">{field.field_name}</label>
                    {field.is_editing ? (
                      <input autoFocus value={field.edit_value} onChange={e => updateEditValue(field.id, e.target.value)}
                        onKeyDown={e => { if (e.key === "Enter") void saveEdit(field.id); }}
                        className="h-[44px] px-[14px] rounded-[6px] text-[#111827] text-[15px] font-semibold border-2 border-[#3a46e5] focus:outline-none" />
                    ) : (
                      <div onClick={() => startEdit(field.id)}
                        className="h-[44px] px-[14px] rounded-[6px] flex items-center text-[#111827] text-[15px] font-semibold border-2 cursor-pointer transition-colors hover:border-[#3a46e5]/50"
                        style={{ borderColor, backgroundColor: bgColor }}>
                        {field.extracted_value || <span className="text-[#94a3b8] font-normal text-[13px]">—</span>}
                      </div>
                    )}
                    {field.needs_review && !field.is_confirmed && (
                      <p className="flex items-center gap-[3px] text-[#d97706] text-[10px] leading-[14px]">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01" stroke="#d97706" strokeWidth="2" strokeLinecap="round"/>
                        </svg>
                        Please verify this is correct
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="flex items-center justify-between pt-[8px] border-t border-[#f1f5f9] mt-[4px]">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="10" width="18" height="11" rx="2" stroke="#94a3b8" strokeWidth="1.5"/>
                <circle cx="12" cy="5" r="2" stroke="#94a3b8" strokeWidth="1.5"/>
                <path d="M12 7v3M8 14h.01M16 14h.01M9 17h6" stroke="#94a3b8" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <button onClick={async () => { await submitFields(); setRightOpen(true); setMobileTab("data"); }}
                className="flex items-center gap-[6px] h-[34px] px-[20px] rounded-[8px] text-white text-[12px] font-semibold cursor-pointer hover:opacity-90 active:scale-[0.98] transition"
                style={{ background: "linear-gradient(135deg, #3a46e5, #6366f1)" }}>
                {source === "db" ? "Update" : "Submit"}
              </button>
            </div>
          </div>
        )}
      </div>
      {/* Bottom nav */}
      <div className="bg-white border-t border-[#e5e7eb] flex items-center justify-between px-[16px] sm:px-[20px] h-[44px] shrink-0">
        <button disabled={currentPage <= 1} onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
          className="flex items-center gap-[4px] text-[#374151] text-[12px] font-medium disabled:opacity-40 hover:text-[#3a46e5] transition">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M15 18l-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
          Previous
        </button>
        <span className="text-[#64748b] text-[12px]">Page {currentPage} of {totalPages}</span>
        <button disabled={currentPage >= totalPages} onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
          className="flex items-center gap-[4px] text-[#374151] text-[12px] font-medium disabled:opacity-40 hover:text-[#3a46e5] transition">
          Next
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
        </button>
      </div>
    </div>
  );

  // Data panel
  const DataPanel = () => (
    <div className="flex flex-col h-full overflow-hidden bg-white">
      <div className="px-[14px] py-[12px] border-b border-[#f1f5f9] shrink-0">
        <div className="flex items-center justify-between mb-[10px]">
          <span className="text-[#0f172a] text-[13px] font-bold tracking-[-0.3px]">Extracted Data</span>
          <button onClick={() => { setRightOpen(false); setMobileTab("viewer"); }}
            className="text-[#94a3b8] hover:text-[#374151] transition p-[2px]">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
        <div className="bg-[#f1f5f9] rounded-full h-[6px] overflow-hidden mb-[4px]">
          <div className="h-full rounded-full bg-[#22c55e] transition-all duration-700" style={{ width: `${avgConfidence}%` }} />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[#94a3b8] text-[11px]">Average confidence</span>
          <span className="text-[#0f172a] text-[12px] font-bold">{avgConfidence}%</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-[10px] py-[10px] flex flex-col gap-[8px]">
        {ocrLoading && (
          <div className="flex flex-col items-center gap-[8px] py-[40px]">
            <Spinner /><p className="text-[#64748b] text-[12px] text-center">Extracting data…</p>
          </div>
        )}
        {!ocrLoading && ocrError && (
          <div className="bg-[#fef2f2] border border-[#fca5a5] rounded-[8px] p-[12px]">
            <p className="text-[#dc2626] text-[12px] leading-[16px]">{ocrError}</p>
            <button onClick={() => fileBlob && void loadFields(fileBlob, fileName)}
              className="mt-[6px] text-[#3a46e5] text-[11px] font-medium hover:underline">Retry OCR</button>
          </div>
        )}
        {!ocrLoading && !ocrError && fields.length === 0 && (
          <div className="text-center py-[40px]">
            <p className="text-[#94a3b8] text-[12px]">No fields extracted yet.</p>
            <button onClick={() => fileBlob && void loadFields(fileBlob, fileName)}
              className="mt-[8px] text-[#3a46e5] text-[12px] font-medium hover:underline">Run OCR</button>
          </div>
        )}
        {fields.map(field => {
          const cb = confBadge(field.confidence_score);
          return (
            <div key={field.id} className={`rounded-[10px] border overflow-hidden ${
              field.is_confirmed ? "border-[#d1fae5]" : field.needs_review ? "border-[#fde68a]" : "border-[#e5e7eb]"
            }`}>
              <div className={`flex items-center justify-between px-[10px] py-[7px] ${
                field.is_confirmed ? "bg-[#dcfce7]" : field.needs_review ? "bg-[#fef3c7]" : "bg-[#f8fafc]"
              }`}>
                <div className="flex items-center gap-[5px] min-w-0">
                  <div className={`size-[14px] rounded-[3px] flex items-center justify-center shrink-0 ${
                    field.is_confirmed ? "bg-[#16a34a]" : field.needs_review ? "bg-[#d97706]" : "bg-[#6366f1]"
                  } bg-opacity-20`}>
                    <svg width="8" height="8" viewBox="0 0 24 24" fill="none">
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"
                        stroke={field.is_confirmed ? "#16a34a" : field.needs_review ? "#d97706" : "#6366f1"}
                        strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  </div>
                  <span className="text-[#111827] text-[11px] font-semibold truncate">{field.field_name}</span>
                </div>
                <span className={`${cb.bg} ${cb.text} text-[10px] font-bold px-[5px] py-[1px] rounded-full shrink-0 ml-[4px]`}>
                  {field.confidence_score}%
                </span>
              </div>
              <div className="px-[10px] pt-[8px]">
                {field.is_editing ? (
                  <input autoFocus value={field.edit_value} onChange={e => updateEditValue(field.id, e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") saveEdit(field.id); }}
                    className="w-full text-[12px] text-[#0f172a] bg-white border border-[#6366f1] rounded-[6px] px-[8px] py-[5px] focus:outline-none" />
                ) : (
                  <p className="text-[#0f172a] text-[13px] font-medium leading-[18px] break-words">
                    {field.extracted_value || <span className="text-[#94a3b8]">—</span>}
                  </p>
                )}
                {field.needs_review && !field.is_confirmed && (
                  <p className="flex items-center gap-[3px] text-[#d97706] text-[10px] mt-[3px] leading-[14px]">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01" stroke="#d97706" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                    Please verify this date is correct
                  </p>
                )}
              </div>
              <div className="flex items-center gap-[4px] px-[10px] py-[7px]">
                {field.is_editing ? (
                  <>
                    <button onClick={() => saveEdit(field.id)} className="text-[#3a46e5] text-[11px] font-medium hover:underline">Save</button>
                    <span className="text-[#e5e7eb] text-[10px]">•</span>
                    <button onClick={() => cancelEdit(field.id)} className="text-[#94a3b8] text-[11px] hover:text-[#374151] transition">Cancel</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => startEdit(field.id)}
                      className="flex items-center gap-[3px] text-[#64748b] text-[11px] font-medium hover:text-[#374151] transition">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                        <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                      </svg>
                      Edit
                    </button>
                    <span className="text-[#e5e7eb] text-[10px]">•</span>
                    {field.is_confirmed ? (
                      <span className="flex items-center gap-[3px] text-[#16a34a] text-[11px] font-medium">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                          <path d="M20 6L9 17l-5-5" stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round"/>
                        </svg>
                        Confirmed
                      </span>
                    ) : (
                      <button onClick={() => confirmField(field.id)}
                        className="flex items-center gap-[3px] text-[#64748b] text-[11px] font-medium hover:text-[#16a34a] transition">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                          <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                        </svg>
                        Confirm
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col bg-[#f9fafb] overflow-hidden"
      style={{ fontFamily: "Inter, sans-serif", height: "calc(100dvh - 56px)" }}>

      {/* ── TOP BAR ── */}
      <div className="bg-white border-b border-[#e5e7eb] flex items-center h-[48px] sm:h-[52px] px-[12px] sm:px-[16px] shrink-0 gap-[8px] sm:gap-[12px]">
        <button onClick={() => navigate(returnAppId ? `/applications/${returnAppId}` : "/documents")}
          className="flex items-center gap-[6px] text-[#64748b] text-[12px] sm:text-[13px] font-medium hover:text-[#0f172a] transition whitespace-nowrap shrink-0">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          <span className="hidden sm:inline">Back to Case</span>
          <span className="sm:hidden">Back</span>
        </button>

        <div className="h-[20px] w-px bg-[#e5e7eb] shrink-0" />

        <div className="flex items-center gap-[8px] min-w-0 flex-1">
          <div className="bg-[#fee2e2] rounded-[5px] flex items-center justify-center w-[28px] h-[32px] shrink-0">
            <span className="text-[#ef4444] text-[7px] font-black">PDF</span>
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-[#0f172a] text-[12px] sm:text-[13px] font-semibold leading-[16px] truncate">{doc.name}</span>
            <span className="text-[#94a3b8] text-[10px] sm:text-[11px] leading-[14px] hidden sm:block">
              Uploaded 2 hours ago {doc.file_size_bytes ? `• ${(doc.file_size_bytes / 1024 / 1024).toFixed(1)} MB` : ""}
            </span>
          </div>
        </div>

        {/* Zoom — hidden on mobile */}
        <div className="hidden sm:flex items-center gap-[3px] shrink-0">
          <button onClick={() => setZoom(z => Math.max(50, z - 10))} className="size-[26px] border border-[#e5e7eb] rounded-[5px] text-[#374151] flex items-center justify-center hover:bg-[#f9fafb] transition text-[14px] font-medium">−</button>
          <span className="text-[#374151] text-[12px] font-medium w-[42px] text-center">{zoom}%</span>
          <button onClick={() => setZoom(z => Math.min(200, z + 10))} className="size-[26px] border border-[#e5e7eb] rounded-[5px] text-[#374151] flex items-center justify-center hover:bg-[#f9fafb] transition text-[14px] font-medium">+</button>
        </div>

        {/* Rotate */}
        <button onClick={() => setRotation(r => (r + 90) % 360)}
          className="hidden sm:flex items-center gap-[5px] h-[30px] px-[10px] border border-[#e5e7eb] rounded-[7px] text-[#374151] text-[12px] font-medium hover:bg-[#f9fafb] transition shrink-0">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
            <path d="M23 4v6h-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          Rotate
        </button>

        {/* Download */}
        <button onClick={handleDownload}
          className="flex items-center gap-[5px] h-[30px] px-[8px] sm:px-[10px] border border-[#e5e7eb] rounded-[7px] text-[#374151] text-[12px] font-medium hover:bg-[#f9fafb] transition shrink-0">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          <span className="hidden sm:inline">Download</span>
        </button>
      </div>

      {/* ── MOBILE TABS ── */}
      <div className="lg:hidden flex items-center border-b border-[#e5e7eb] bg-white shrink-0">
        {([
          { id: "pages",  label: "Pages"  },
          { id: "viewer", label: "Viewer" },
          { id: "data",   label: `Data${fields.length > 0 ? ` (${fields.length})` : ""}` },
        ] as const).map(tab => (
          <button key={tab.id} onClick={() => setMobileTab(tab.id)}
            className={`flex-1 py-[10px] text-[13px] font-medium border-b-2 transition-colors ${
              mobileTab === tab.id
                ? "border-[#3a46e5] text-[#3a46e5]"
                : "border-transparent text-[#6b7280]"
            }`}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── BODY ── */}
      {/* Mobile: show one tab at a time */}
      <div className="lg:hidden flex-1 min-h-0 overflow-hidden">
        {mobileTab === "pages"  && <PagesPanel />}
        {mobileTab === "viewer" && <ViewerPanel />}
        {mobileTab === "data"   && <DataPanel  />}
      </div>

      {/* Desktop: 3-panel side by side */}
      <div className="hidden lg:flex flex-1 min-h-0 overflow-hidden">
        <div className="w-[168px] shrink-0 border-r border-[#e5e7eb]"><PagesPanel /></div>
        <ViewerPanel />
        {rightOpen && (
          <div className="w-[280px] shrink-0 border-l border-[#e5e7eb]"><DataPanel /></div>
        )}
        {!rightOpen && fields.length > 0 && (
          <div className="absolute bottom-[56px] right-[16px]">
            <button onClick={async () => { await submitFields(); setRightOpen(true); }}
              className="flex items-center gap-[6px] h-[34px] px-[12px] rounded-[8px] bg-white border border-[#e5e7eb] text-[#374151] text-[12px] font-medium shadow-md hover:bg-[#f9fafb] transition">
              {source === "db" ? "Update" : "Submit"}
            </button>
          </div>
        )}
      </div>

      {/* ── BOTTOM STATUS BAR ── */}
      <div className="bg-white border-t border-[#e5e7eb] flex items-center justify-between h-[48px] px-[12px] sm:px-[16px] shrink-0">
        <div className="flex items-center gap-[10px] sm:gap-[14px]">
          <span className="flex items-center gap-[5px] text-[10px] sm:text-[11px] text-[#374151]">
            <span className="size-[7px] rounded-full bg-[#22c55e] shrink-0" />
            {confirmedCount} confirmed
          </span>
          {reviewCount > 0 && (
            <span className="flex items-center gap-[5px] text-[10px] sm:text-[11px] text-[#d97706]">
              <span className="size-[7px] rounded-full bg-[#f59e0b] shrink-0" />
              {reviewCount} review
            </span>
          )}
        </div>
        <button onClick={exportData}
          className="flex items-center gap-[6px] h-[32px] px-[14px] rounded-[8px] text-white text-[12px] font-semibold hover:opacity-90 transition"
          style={{ background: 'linear-gradient(135deg, #3a46e5, #6366f1)' }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
              stroke="white" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          Export Data
        </button>
      </div>
    </div>
  );
}