// src/pages/employee/DocumentHub.tsx
import { useRef, useState } from "react";
import { useNavigate }      from "react-router-dom";
import { useDocumentHub }   from "../../hooks/employee/useDocumentHub";
import type { HubDocument, RequirementItem } from "../../types/employee/documentHub.types";

import imgUpload      from "../../assets/icons/appdetail-upload-cloud.svg";
import imgPdf         from "../../assets/icons/docup-pdf-icon.svg";
import imgDocx        from "../../assets/icons/dochub-docx.svg";
import imgImg         from "../../assets/icons/dochub-img.svg";
import imgListView    from "../../assets/icons/dochub-list-view.svg";
import imgGridView    from "../../assets/icons/dochub-grid-view.svg";
import imgStorage     from "../../assets/icons/dochub-storage.svg";
import imgVerified    from "../../assets/icons/dochub-verified.svg";
import imgPending     from "../../assets/icons/dochub-pending.svg";
import imgMissing     from "../../assets/icons/dochub-missing.svg";
import imgActivityDot from "../../assets/icons/dochub-activity-dot.svg";

function fmtSize(bytes: number): string {
  if (!bytes) return "0 KB";
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.round(bytes / 1024)} KB`;
}
function fmtDate(iso?: string): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
function fmtRelative(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso), now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
  if (diff < 86400)  return `Today, ${d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}`;
  if (diff < 172800) return `Yesterday, ${d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}`;
  return fmtDate(iso);
}
function getFileIcon(type: string) {
  if (type === "pdf") return imgPdf;
  if (type === "docx") return imgDocx;
  return imgImg;
}
function getFileLabel(type: string) {
  if (type === "pdf") return "PDF";
  if (type === "docx") return "DOCX";
  if (type === "img") return "IMG";
  return "FILE";
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    verified:       { bg: "bg-[#d1fae5]", text: "text-[#065f46]", label: "Verified" },
    pending_review: { bg: "bg-[#fef3c7]", text: "text-[#92400e]", label: "Pending Review" },
    uploaded:       { bg: "bg-[#dbeafe]", text: "text-[#1e40af]", label: "Uploaded" },
    rejected:       { bg: "bg-[#fee2e2]", text: "text-[#991b1b]", label: "Rejected" },
    required:       { bg: "bg-[#f3f4f6]", text: "text-[#374151]", label: "Required" },
    missing:        { bg: "bg-[#fee2e2]", text: "text-[#991b1b]", label: "Missing" },
  };
  const s = map[status] ?? map.uploaded;
  return (
    <span className={`${s.bg} ${s.text} text-[11px] font-semibold px-[8px] py-[3px] rounded-full leading-[16px] whitespace-nowrap`}>
      {s.label}
    </span>
  );
}

function ReqIcon({ status }: { status: string }) {
  if (status === "verified" || status === "uploaded") return <img src={imgVerified} alt="" className="size-[20px] shrink-0" />;
  if (status === "pending_review") return <img src={imgPending} alt="" className="size-[20px] shrink-0" />;
  return <img src={imgMissing} alt="" className="size-[20px] shrink-0" />;
}

function DocCard({ doc }: { doc: HubDocument }) {
  const navigate = useNavigate();
  return (
    <div onClick={() => doc.id && navigate(`/documents/viewer?doc_id=${doc.id}`)}
         className="bg-white border border-[#f1f5f9] rounded-[16px] shadow-[0px_1px_4px_rgba(0,0,0,0.04)] flex flex-col gap-[12px] p-[20px] cursor-pointer hover:border-[#6366f1]/30 hover:shadow-[0px_4px_16px_rgba(99,102,241,0.08)] transition-all duration-200">
      <div className="flex items-start justify-between">
        <img src={getFileIcon(doc.file_type)} alt={doc.file_type} className="w-[44px] h-[52px] object-contain" />
        <span className="text-[#94a3b8] text-[11px] font-semibold tracking-[0.5px] uppercase">{getFileLabel(doc.file_type)}</span>
      </div>
      <div className="flex flex-col gap-[2px]">
        <p className="text-[#111827] text-[13px] font-semibold leading-[18px] line-clamp-2">{doc.name}</p>
        {doc.application_name && <p className="text-[#94a3b8] text-[11px] leading-[16px] truncate">{doc.application_name}</p>}
      </div>
      <div className="flex items-center justify-between mt-auto pt-[4px] border-t border-[#f8fafc]">
        <StatusBadge status={doc.status} />
        <span className="text-[#94a3b8] text-[11px]">{fmtDate(doc.uploaded_at)}</span>
      </div>
    </div>
  );
}

function DocRow({ doc }: { doc: HubDocument }) {
  const navigate = useNavigate();
  return (
    <div onClick={() => doc.id && navigate(`/documents/viewer?doc_id=${doc.id}`)}
         className="flex items-center gap-[16px] px-[20px] py-[14px] border-b border-[#f8fafc] last:border-0 hover:bg-[#f8fafc] cursor-pointer transition-colors">
      <img src={getFileIcon(doc.file_type)} alt={doc.file_type} className="w-[32px] h-[38px] object-contain shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-[#111827] text-[13px] font-semibold truncate">{doc.name}</p>
        <p className="text-[#94a3b8] text-[11px] truncate">{doc.application_name ?? doc.document_type} • {fmtSize(doc.file_size_bytes)}</p>
      </div>
      <StatusBadge status={doc.status} />
      <span className="text-[#94a3b8] text-[12px] shrink-0 hidden sm:block">{fmtDate(doc.uploaded_at)}</span>
    </div>
  );
}

function ReqItem({ item, onUpload }: { item: RequirementItem; onUpload: (id: string) => void }) {
  const isMissing = item.status === "missing" || item.status === "required";
  const isPending = item.status === "pending_review";
  return (
    <div className={`flex flex-col gap-[4px] p-[12px] rounded-[10px] border ${isMissing ? "bg-white border-[#f1f5f9]" : isPending ? "bg-[#fffbeb] border-[#fde68a]" : "bg-[#f0fdf4] border-[#d1fae5]"}`}>
      <div className="flex items-center gap-[10px]">
        <ReqIcon status={item.status} />
        <div className="flex-1 min-w-0">
          <p className="text-[#111827] text-[13px] font-semibold leading-[18px] truncate">{item.task_name}</p>
          <p className={`text-[11px] leading-[14px] ${isMissing ? "text-[#ef4444]" : isPending ? "text-[#d97706]" : "text-[#059669]"}`}>
            {isMissing ? "Missing Document" : isPending ? "Pending Review" : "Uploaded & Verified"}
          </p>
        </div>
      </div>
      {isMissing && (
        <button onClick={e => { e.stopPropagation(); onUpload(item.id); }}
                className="mt-[4px] w-full h-[28px] rounded-[7px] text-white text-[12px] font-medium hover:opacity-90 transition"
                style={{ background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)" }}>
          Upload Now
        </button>
      )}
    </div>
  );
}

export default function DocumentHub() {
  const navigate   = useNavigate();
  const fileRef    = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const {
    documents, requirements, activity, storage, applicationTabs,
    isLoading, error, uploading, uploadError,
    viewMode, setViewMode,
    activeFilter, setActiveFilter,
    searchQuery, setSearchQuery,
    uploadDocument,
  } = useDocumentHub();

  const storagePct = Math.min(100, Math.round((storage.used_mb / storage.total_mb) * 100));
  const usedLabel  = `${storage.used_mb.toFixed(1)} MB of ${storage.total_mb} MB`;

  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadDocument(file);
  }
  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) uploadDocument(file);
    e.target.value = "";
  }
  function handleUploadToTask(taskId: string) {
    const appId = activeFilter !== "all" ? activeFilter : "";
    navigate(`/documents/upload?application_id=${appId}&task_id=${taskId}`);
  }

  // Status dot colour for application tabs
  function tabDot(status: string) {
    if (status === "in_progress") return "bg-[#22c55e]";
    if (status === "submitted")   return "bg-[#3b82f6]";
    if (status === "approved")    return "bg-[#059669]";
    return "bg-[#94a3b8]";
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden" style={{ fontFamily: "Inter, sans-serif" }}>

      {/* TOP HEADER */}
      <header className="bg-white border-b border-[#f1f5f9] shrink-0 flex items-center justify-between px-[24px] sm:px-[32px] h-[64px] gap-[16px]">
        <h1 className="text-[#0f172a] text-[20px] font-bold tracking-[-0.5px] shrink-0">Document Hub</h1>

        {/* Dynamic filter tabs */}
        <div className="flex items-center gap-[4px] overflow-x-auto">
          {/* All Documents — always first */}
          <button onClick={() => setActiveFilter("all")}
                  className={`px-[14px] py-[6px] rounded-full text-[13px] font-medium whitespace-nowrap transition-colors ${activeFilter === "all" ? "bg-[#6366f1] text-white" : "text-[#64748b] hover:bg-[#f1f5f9]"}`}>
            All Documents
          </button>

          {/* One tab per real application */}
          {applicationTabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveFilter(tab.id)}
                    className={`px-[14px] py-[6px] rounded-full text-[13px] font-medium whitespace-nowrap transition-colors flex items-center gap-[5px] ${activeFilter === tab.id ? "bg-[#6366f1] text-white" : "text-[#64748b] hover:bg-[#f1f5f9]"}`}>
              {tab.label}
              <span className={`size-[6px] rounded-full inline-block ${tabDot(tab.status)} ${activeFilter === tab.id ? "opacity-70" : ""}`} />
            </button>
          ))}
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-[12px] shrink-0">
          {/* Search */}
          <div className="relative hidden md:block">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" className="absolute left-[11px] top-1/2 -translate-y-1/2 text-[#94a3b8]">
              <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
              <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            <input type="text" placeholder="Search documents..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                   className="pl-[34px] pr-[12px] py-[7px] text-[13px] bg-[#f8fafc] border border-[#f1f5f9] rounded-[10px] focus:outline-none focus:border-[#6366f1] focus:ring-1 focus:ring-[#6366f1]/20 transition w-[200px]"
                   style={{ fontFamily: "Inter, sans-serif" }} />
          </div>

          {/* Storage */}
          <div className="hidden lg:flex items-center gap-[8px]">
            <img src={imgStorage} alt="" className="w-[16px] h-[16px]" />
            <div className="flex flex-col gap-[2px]">
              <div className="bg-[#e2e8f0] rounded-full h-[4px] w-[80px] overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500"
                     style={{ width: `${storagePct}%`, background: storagePct > 80 ? "linear-gradient(90deg,#ef4444,#f97316)" : "linear-gradient(90deg,#6366f1,#8b5cf6)" }} />
              </div>
              <span className="text-[10px] text-[#94a3b8] whitespace-nowrap">Storage: {usedLabel}</span>
            </div>
          </div>

          {/* Notification */}
          <button onClick={() => navigate("/notifications")}
                  className="bg-white border border-[#e2e8f0] rounded-[10px] flex items-center justify-center size-[36px] hover:bg-[#f8fafc] transition relative">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0" stroke="#64748b" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
      </header>

      {/* MAIN */}
      <main className="flex-1 overflow-y-auto px-[16px] sm:px-[24px] lg:px-[32px] py-[24px] sm:py-[28px]">
        <div className="flex gap-[24px] items-start max-w-[1400px] mx-auto">

          {/* LEFT — Upload + Docs */}
          <div className="flex flex-col gap-[24px] flex-1 min-w-0">

            {/* Upload zone */}
            <div className="bg-white border border-[#f1f5f9] rounded-[16px] shadow-[0px_1px_4px_rgba(0,0,0,0.04)] p-[24px]">
              <div className="flex items-center justify-between mb-[16px]">
                <h2 className="text-[#0f172a] text-[16px] font-bold tracking-[-0.3px]">Upload New Document</h2>
                {/* <button className="text-[#6366f1] text-[13px] font-medium hover:underline">View Supported Formats</button> */}
                <div className="relative group">
                  <button
                    type="button"
                    className="text-[#6366f1] text-[13px] font-medium hover:underline"
                  >
                    View Supported Formats
                  </button>

                  {/* Popup */}
                  <div className="absolute right-0 top-[28px] z-20 hidden group-hover:flex flex-col gap-[10px]
                                  min-w-[240px] bg-white border border-[#e2e8f0]
                                  rounded-[14px] shadow-[0px_8px_30px_rgba(0,0,0,0.08)]
                                  p-[16px]">

                    <div>
                      <p className="text-[#0f172a] text-[13px] font-semibold mb-[6px]">
                        Supported File Types
                      </p>

                      <div className="flex flex-wrap gap-[8px]">
                        <span className="px-[10px] py-[5px] rounded-full bg-[#f1f5f9] text-[#334155] text-[11px] font-medium">
                          PDF
                        </span>

                        <span className="px-[10px] py-[5px] rounded-full bg-[#f1f5f9] text-[#334155] text-[11px] font-medium">
                          DOCX
                        </span>

                        <span className="px-[10px] py-[5px] rounded-full bg-[#f1f5f9] text-[#334155] text-[11px] font-medium">
                          JPG
                        </span>

                        <span className="px-[10px] py-[5px] rounded-full bg-[#f1f5f9] text-[#334155] text-[11px] font-medium">
                          JPEG
                        </span>

                        <span className="px-[10px] py-[5px] rounded-full bg-[#f1f5f9] text-[#334155] text-[11px] font-medium">
                          PNG
                        </span>

                        <span className="px-[10px] py-[5px] rounded-full bg-[#f1f5f9] text-[#334155] text-[11px] font-medium">
                          GIF
                        </span>
                      </div>
                    </div>

                    <div className="border-t border-[#f1f5f9] pt-[10px]">
                      <p className="text-[#64748b] text-[11px] leading-[16px]">
                        Maximum upload size depends on your storage plan.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={handleDrop} onClick={() => fileRef.current?.click()}
                   className={`border-2 border-dashed rounded-[14px] flex flex-col items-center justify-center gap-[10px] py-[32px] cursor-pointer transition-all duration-200 ${dragging ? "border-[#6366f1] bg-[#f0f0ff]" : uploading ? "border-[#6366f1]/40 bg-[#fafafe]" : "border-[#e2e8f0] bg-[#fafafe] hover:border-[#6366f1]/60 hover:bg-[#f5f5ff]"}`}>
                {uploading ? (
                  <>
                    <svg className="w-8 h-8 animate-spin text-[#6366f1]" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                    </svg>
                    <p className="text-[#6366f1] text-[14px] font-medium">Uploading…</p>
                  </>
                ) : (
                  <>
                    <img src={imgUpload} alt="" className="w-[48px] h-[48px]" />
                    <div className="text-center">
                      <p className="text-[#0f172a] text-[15px] font-semibold">Drag and drop files here</p>
                      <p className="text-[#94a3b8] text-[13px] mt-[2px]">or click to browse your computer</p>
                    </div>
                    <button onClick={e => { e.stopPropagation(); fileRef.current?.click(); }}
                            className="bg-white border border-[#e2e8f0] text-[#374151] text-[13px] font-medium px-[20px] py-[8px] rounded-[8px] hover:bg-[#f8fafc] transition">
                      Browse Files
                    </button>
                  </>
                )}
              </div>
              {uploadError && <p className="text-[#ef4444] text-[13px] mt-[10px]">{uploadError}</p>}
              <input ref={fileRef} type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png,.docx,.doc" onChange={handleFileChange} />
            </div>

            {/* Documents list */}
            <div className="bg-white border border-[#f1f5f9] rounded-[16px] shadow-[0px_1px_4px_rgba(0,0,0,0.04)] overflow-hidden">
              <div className="flex items-center justify-between px-[20px] py-[16px] border-b border-[#f8fafc]">
                <div className="flex items-center gap-[8px]">
                  <h2 className="text-[#0f172a] text-[16px] font-bold tracking-[-0.3px]">Recent Documents</h2>
                  {documents.length > 0 && (
                    <span className="bg-[#f1f5f9] text-[#64748b] text-[11px] font-semibold px-[8px] py-[2px] rounded-full">{documents.length}</span>
                  )}
                </div>
                <div className="flex items-center gap-[2px]">
                  <button onClick={() => setViewMode("list")} className={`p-[7px] rounded-[7px] transition ${viewMode === "list" ? "bg-[#6366f1]" : "text-[#94a3b8] hover:bg-[#f1f5f9]"}`}>
                    <img src={imgListView} alt="list" className={`w-[16px] h-[16px] ${viewMode === "list" ? "brightness-0 invert" : ""}`} />
                  </button>
                  <button onClick={() => setViewMode("grid")} className={`p-[7px] rounded-[7px] transition ${viewMode === "grid" ? "bg-[#6366f1]" : "text-[#94a3b8] hover:bg-[#f1f5f9]"}`}>
                    <img src={imgGridView} alt="grid" className={`w-[16px] h-[16px] ${viewMode === "grid" ? "brightness-0 invert" : ""}`} />
                  </button>
                </div>
              </div>

              {isLoading && (
                <div className="flex items-center justify-center py-[64px]">
                  <svg className="w-7 h-7 animate-spin text-[#6366f1]" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                </div>
              )}
              {!isLoading && error && <div className="flex items-center justify-center py-[64px]"><p className="text-[#ef4444] text-[14px]">{error}</p></div>}
              {!isLoading && !error && documents.length === 0 && (
                <div className="flex flex-col items-center gap-[12px] py-[48px]">
                  <div className="bg-[#f1f5f9] rounded-full p-[16px]">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="#94a3b8" strokeWidth="1.5" strokeLinecap="round"/>
                    </svg>
                  </div>
                  <p className="text-[#64748b] text-[14px]">{activeFilter === "all" ? "No documents yet" : "No documents for this application yet"}</p>
                </div>
              )}
              {!isLoading && !error && documents.length > 0 && viewMode === "grid" && (
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-[16px] p-[20px]">
                  {documents.map(doc => <DocCard key={doc.id} doc={doc} />)}
                </div>
              )}
              {!isLoading && !error && documents.length > 0 && viewMode === "list" && (
                <div className="flex flex-col">{documents.map(doc => <DocRow key={doc.id} doc={doc} />)}</div>
              )}
            </div>
          </div>

          {/* RIGHT sidebar */}
          <div className="hidden lg:flex flex-col gap-[20px] w-[280px] shrink-0">

            {/* Requirements — updates when you click a different tab */}
            {requirements ? (
              <div className="bg-white border border-[#f1f5f9] rounded-[16px] shadow-[0px_1px_4px_rgba(0,0,0,0.04)] p-[20px]">
                <div className="flex items-center justify-between mb-[16px]">
                  <h3 className="text-[#0f172a] text-[15px] font-bold tracking-[-0.3px]">{requirements.visa_code} Requirements</h3>
                  <span className="bg-[#f0fdf4] border border-[#d1fae5] text-[#059669] text-[11px] font-semibold px-[8px] py-[3px] rounded-full">
                    {requirements.done}/{requirements.total} Done
                  </span>
                </div>
                <div className="flex flex-col gap-[10px]">
                  {requirements.items.map(item => (
                    <ReqItem key={item.id} item={item} onUpload={handleUploadToTask} />
                  ))}
                </div>
                <button onClick={() => navigate(`/applications/${requirements.application_id}`)}
                        className="mt-[12px] w-full text-center text-[#6366f1] text-[12px] font-medium hover:underline">
                  View Application Detail →
                </button>
              </div>
            ) : activeFilter !== "all" ? (
              <div className="bg-white border border-[#f1f5f9] rounded-[16px] shadow-[0px_1px_4px_rgba(0,0,0,0.04)] p-[20px]">
                <div className="flex items-center justify-center py-[24px]">
                  <svg className="w-5 h-5 animate-spin text-[#6366f1]" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                </div>
              </div>
            ) : null}

            {/* Recent Activity */}
            <div className="bg-white border border-[#f1f5f9] rounded-[16px] shadow-[0px_1px_4px_rgba(0,0,0,0.04)] p-[20px]">
              <h3 className="text-[#0f172a] text-[15px] font-bold tracking-[-0.3px] mb-[16px]">Recent Activity</h3>
              {activity.length === 0 ? (
                <p className="text-[#94a3b8] text-[13px]">No recent activity.</p>
              ) : (
                <div className="flex flex-col gap-[14px]">
                  {activity.map(item => (
                    <div key={item.id} className="flex gap-[10px] items-start">
                      <img src={imgActivityDot} alt="" className="w-[8px] h-[8px] mt-[5px] shrink-0" />
                      <div className="flex flex-col gap-[2px] min-w-0">
                        <p className="text-[#0f172a] text-[12px] font-medium leading-[16px]">{item.text}</p>
                        <p className="text-[#94a3b8] text-[11px] leading-[14px]">by {item.by} • {fmtRelative(item.timestamp)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <button className="mt-[16px] w-full text-center text-[#6366f1] text-[12px] font-medium hover:underline">View All Activity</button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}