// // src/pages/employee/NewApplication.tsx
// import { useState,useEffect} from "react";
// import { useNavigate, Link } from "react-router-dom";
// import { createApplication } from "../../api/applications.api";
// import { PageHeader, PageContent } from "../../components/layout/PageHeader";
// import { useCurrentUser } from "../../hooks/useAuth";
// import { useVisaTypes } from "../../hooks/useApplications";
// import { Lock, Save, ArrowRight, Loader2 } from "lucide-react";
// import type { AxiosError } from "axios";

// // ── Assets ────────────────────────────────────────────────────────────────────
// // import imgCheckGreen  from "../../assets/icons/check-green.svg";
// import imgRadioFilled from "../../assets/icons/radio-filled.svg";
// import imgReqDot      from "../../assets/icons/req-dot.svg";

// // ─────────────────────────────────────────────────────────────────────────────
// export default function NewApplication() {
//   const navigate = useNavigate();

//   const { data: user }                                                   = useCurrentUser();
//   const { data: visaTypesRaw, isLoading: visaLoading, error: visaError } = useVisaTypes();
//   const visaTypes = visaTypesRaw ?? [];

//   // ── Form state ────────────────────────────────────────────────────────────
//   const [selectedVisaId,  setSelectedVisaId]  = useState<string>("");
//   const [sponsorEmployer, setSponsorEmployer] = useState("");
//   const [notes,           setNotes]           = useState("");
//   const [loading,         setLoading]         = useState(false);
//   const [error,           setError]           = useState<string | null>(null);

//   // Auto-select first visa type once loaded
//   useEffect(() => {
//     if (visaTypes.length > 0 && !selectedVisaId) {
//       setSelectedVisaId(visaTypes[0].id);
//     }
//   }, [visaTypes.length]); // eslint-disable-line react-hooks/exhaustive-deps

//   const selectedVisa = visaTypes.find(v => v.id === selectedVisaId);
//   const fullName     = user ? `${user.first_name} ${user.last_name}` : "—";
//   const email        = user?.email ?? "—";
//   const role         = user?.roles?.[0] ?? "employee";
// 
//   // ── Submit ────────────────────────────────────────────────────────────────
//   async function handleSubmit(isDraft: boolean) {
//     if (!selectedVisaId) { setError("Please select a visa type."); return; }
//     setLoading(true);
//     setError(null);
//     try {
//       const app = await createApplication({
//         visa_type_id:     selectedVisaId,
//         sponsor_employer: sponsorEmployer || undefined,
//         notes:            notes || undefined,
//       });
//       if (!app?.id) {
//         setError("Application created but ID missing. Please check your applications list.");
//         return;
//       }
//       navigate(isDraft ? "/applications/list" : `/documents/upload?application_id=${app.id}`);
//     } catch (e: unknown) {
//       const err = e as AxiosError<{ detail: string }>;
//       const httpStatus = err.response?.status;
//       if (httpStatus === 409) {
//         setError(
//           err.response?.data?.detail ??
//           "You already have a draft for this visa type. Please complete or delete it first."
//         );
//       } else {
//         setError(
//           err.response?.data?.detail ??
//           (e instanceof Error ? e.message : "Something went wrong.")
//         );
//       }
//     } finally {
//       setLoading(false);
//     }
//   }

//   return (
//     <div className="flex flex-col flex-1 min-h-0 overflow-hidden" style={{ fontFamily: "Inter, sans-serif" }}>

//       {/* TOP HEADER */}
//       <header className="bg-white border-b border-[#f1f5f9] flex h-[72px] items-center
//                          justify-between px-[32px] shrink-0 sticky top-0 z-10">

//         <nav className="flex items-center gap-[8px]">
//           <Link
//             to="/applications"
//             className="text-[#64748b] text-[14px] font-normal tracking-[-0.5px] leading-[20px]
//                        hover:text-[#0f172a] transition-colors"
//           >
//             Applications
//           </Link>
//           <ChevronRight size={12} className="text-[#94a3b8] shrink-0" />
//           <span className="text-[#0f172a] text-[14px] font-medium tracking-[-0.5px] leading-[20px]">
//             New Application
//           </span>
//         </nav>

//         <div className="flex items-center gap-[16px] h-[40px]">
//           <button
//             type="button"
//             className="bg-white border border-[#e2e8f0] drop-shadow-[0px_1px_1px_rgba(0,0,0,0.05)]
//                        flex items-center justify-center rounded-[12px] shrink-0 size-[40px]
//                        hover:bg-[#f8fafc] transition-colors"
//             aria-label="Search"
//           >
//             <Search size={16} className="text-[#64748b]" />
//           </button>

//           <button
//             type="button"
//             onClick={() => navigate("/notifications")}
//             className="bg-white border border-[#e2e8f0] drop-shadow-[0px_1px_1px_rgba(0,0,0,0.05)]
//                        flex items-center justify-center relative rounded-[12px] shrink-0 size-[40px]
//                        hover:bg-[#f8fafc] transition-colors"
//             aria-label="Notifications"
//           >
//             <Bell size={14} className="text-[#64748b]" />
//             <span className="absolute bg-[#5269f2] border border-white h-[8px] w-[8px]
//                              rounded-full top-[8px] right-[10px]" />
//           </button>

//           <button
//             type="button"
//             onClick={() => navigate("/profile")}
//             className="flex items-center gap-[12px] border-l border-[#e2e8f0] pl-[17px] h-[34px]
//                        hover:opacity-80 transition-opacity overflow-clip"
//           >
//             <img src={imgUserAvatar} alt="" className="rounded-full object-cover shrink-0 size-[32px]" />
//             <div className="flex flex-col items-start">
//               <p className="text-[#0f172a] text-[14px] font-semibold tracking-[-0.5px] leading-[18px] whitespace-nowrap">
//                 {fullName}
//               </p>
//               <p className="text-[#64748b] text-[12px] font-normal tracking-[-0.5px] leading-[16px] whitespace-nowrap">
//                 {roleLabel}
//               </p>
//             </div>
//           </button>
//         </div>
//       </header>

//       {/* SCROLLABLE CONTENT */}
//       <main className="flex-1 overflow-y-auto px-[16px] sm:px-[24px] lg:px-[48px] py-[24px] sm:py-[32px]">
//         <div className="max-w-[800px] flex flex-col gap-[40px]">

//           <h1 className="text-[#0f172a] text-[24px] font-bold tracking-[-0.5px] leading-[32px] whitespace-nowrap">
//             Create New Application
//           </h1>

//           {/* Step indicator */}
//           <div className="bg-white border border-[#f1f5f9] rounded-[16px]
//                           shadow-[0px_4px_12px_0px_rgba(0,0,0,0.02)]
//                           flex items-center justify-between h-[54px] p-[17px] overflow-clip">

//             <div className="flex items-center gap-[8px] px-[8px]">
//               <div className="bg-[#ecfdf5] flex items-center justify-center rounded-full shrink-0 size-[20px]">
//                 <img src={imgCheckGreen} alt="" className="w-[8.75px] h-[10px] object-contain" />
//               </div>
//               <span className="text-[#059669] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
//                 Profile Check
//               </span>
//             </div>

//             <div className="bg-[#e2e8f0] h-px w-[32px] shrink-0" />

//             <div className="flex items-center gap-[8px] px-[8px]">
//               <div className="bg-[#3a46e5] flex items-center justify-center rounded-full shrink-0 size-[20px]">
//                 <span className="text-white text-[12px] font-medium tracking-[-0.5px] leading-[16px]">2</span>
//               </div>
//               <span className="text-[#3a46e5] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
//                 Visa Type
//               </span>
//             </div>

//             <div className="bg-[#e2e8f0] h-px w-[32px] shrink-0" />

//             <div className="flex items-center gap-[8px] px-[8px] opacity-50">
//               <div className="bg-[#f1f5f9] flex items-center justify-center rounded-full shrink-0 size-[20px]">
//                 <span className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">3</span>
//               </div>
//               <span className="text-[#64748b] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
//                 Requirements
//               </span>
//             </div>

//             <div className="bg-[#e2e8f0] h-px w-[32px] shrink-0" />

//             <div className="flex items-center gap-[8px] px-[8px] opacity-50">
//               <div className="bg-[#f1f5f9] flex items-center justify-center rounded-full shrink-0 size-[20px]">
//                 <span className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">4</span>
//               </div>
//               <span className="text-[#64748b] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
//                 Review
//               </span>
//             </div>
//           </div>

//           {/* Errors */}
//           {(error || visaError) && (
//             <div className="bg-[#fef2f2] border border-[#fca5a5] text-[#dc2626] rounded-[12px]
//                             px-[16px] py-[12px] text-[14px] tracking-[-0.5px]">
//               {error ?? visaError}
//             </div>
//           )}

//           {/* Section 1: Applicant Information */}
//           <div className="bg-white border border-[#f1f5f9] rounded-[16px]
//                           drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)] p-[25px] flex flex-col gap-[24px]">

//             <div className="flex items-center justify-between pb-[17px] border-b border-[#f1f5f9]">
//               <p className="text-[#0f172a] text-[18px] font-semibold tracking-[-0.5px] leading-[28px]">
//                 Applicant Information
//               </p>
//               <span className="bg-[#f0f5ff] border border-[#e5edff] text-[#2f35ca] text-[12px]
//                                font-medium tracking-[-0.5px] leading-[16px] px-[10px] py-[5px] rounded-[6px]">
//                 Prefilled
//               </span>
//             </div>

//             <div className="grid grid-cols-1 sm:grid-cols-2 gap-[16px] sm:gap-[24px]">

//               <div className="flex flex-col gap-[6px]">
//                 <label className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">
//                   Full Name
//                 </label>
//                 <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[12px] h-[42px]
//                                 flex items-center justify-between px-[17px] py-[11px]">
//                   <span className="text-[#0f172a] text-[14px] font-normal tracking-[-0.5px] leading-[20px] truncate">
//                     {fullName}
//                   </span>
//                   <Lock size={10} className="text-[#94a3b8] shrink-0 ml-2" />
//                 </div>
//               </div>

//               <div className="flex flex-col gap-[6px]">
//                 <label className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">
//                   Email Address
//                 </label>
//                 <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[12px] h-[42px]
//                                 flex items-center justify-between px-[17px] py-[11px]">
//                   <span className="text-[#0f172a] text-[14px] font-normal tracking-[-0.5px] leading-[20px] truncate">
//                     {email}
//                   </span>
//                   <Lock size={10} className="text-[#94a3b8] shrink-0 ml-2" />
//                 </div>
//               </div>

//               {/* <div className="flex flex-col gap-[6px]">
//                 <label className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">
//                   Current Nationality
//                 </label>
//                 <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[12px] h-[42px]
//                                 flex items-center justify-between px-[17px] py-[11px]">
//                   <span className="text-[#0f172a] text-[14px] font-normal tracking-[-0.5px] leading-[20px]">
//                     {fullName}
//                   </span>
//                   <Lock size={10} className="text-[#94a3b8] shrink-0 ml-2" />
//                 </div>
//               </div> */}

//               <div className="flex flex-col gap-[6px]">
//                 <label className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">
//                   Sponsoring Employer
//                 </label>
//                 <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[12px] h-[42px]
//                                 flex items-center px-[17px] py-[11px]
//                                 focus-within:border-[#3a46e5] focus-within:ring-1
//                                 focus-within:ring-[#3a46e5] transition-colors">
//                   <input
//                     type="text"
//                     value={sponsorEmployer}
//                     onChange={e => setSponsorEmployer(e.target.value)}
//                     placeholder="e.g. TechCorp Inc."
//                     className="bg-transparent text-[#0f172a] text-[14px] font-normal tracking-[-0.5px]
//                                leading-[20px] w-full focus:outline-none placeholder:text-[#94a3b8]"
//                     style={{ fontFamily: "Inter, sans-serif" }}
//                   />
//                 </div>
//               </div>
//             </div>

//             <div className="flex justify-end">
//               <Link
//                 to="/profile"
//                 className="text-[#3a46e5] text-[14px] font-medium tracking-[-0.5px] leading-[20px] hover:underline"
//               >
//                 Edit Profile Data
//               </Link>
//             </div>
//           </div>

//           {/* Section 2: Select Visa Type */}
//           <div className="bg-white border border-[#f1f5f9] rounded-[16px]
//                           drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)] p-[25px] flex flex-col gap-[24px]">
//             <p className="text-[#0f172a] text-[18px] font-semibold tracking-[-0.5px] leading-[28px]">
//               Select Visa Type
//             </p>

//             {visaLoading && (
//               <div className="flex items-center justify-center py-[32px]">
//                 <Loader2 size={24} className="animate-spin text-[#3a46e5]" />
//               </div>
//             )}

//             {!visaLoading && (
//               <div className="flex flex-col gap-[16px]">
//                 {visaTypes.map(visa => {
//                   const isSelected = selectedVisaId === visa.id;
//                   return (
//                     <label
//                       key={visa.id}
//                       onClick={() => setSelectedVisaId(visa.id)}
//                       className={`flex gap-[12px] p-[17px] rounded-[12px] border cursor-pointer transition-colors ${
//                         isSelected
//                           ? "bg-[rgba(240,245,255,0.3)] border-[#5269f2]"
//                           : "bg-white border-[#e2e8f0] hover:border-[#5269f2] hover:bg-[rgba(240,245,255,0.1)]"
//                       }`}
//                     >
//                       <div className="flex items-start pt-[2px] shrink-0 w-[16px]">
//                         {isSelected ? (
//                           <div className="bg-white border-[0.5px] border-[#0075ff] rounded-full
//                                           p-[2px] flex items-center justify-center shrink-0 size-[16px]">
//                             <img src={imgRadioFilled} alt="" className="size-[12.8px] object-contain" />
//                           </div>
//                         ) : (
//                           <div className="bg-white border-[0.5px] border-black rounded-full shrink-0 size-[16px]" />
//                         )}
//                       </div>
//                       <div className="flex flex-col gap-[4px] flex-1 min-w-0">
//                         <span className="text-[#0f172a] text-[14px] font-semibold tracking-[-0.5px] leading-[20px]">
//                           {visa.name}
//                         </span>
//                         <span className="text-[#64748b] text-[12px] font-normal tracking-[-0.5px] leading-[16px]">
//                           {visa.description}
//                         </span>
//                       </div>
//                     </label>
//                   );
//                 })}

//                 {visaTypes.length === 0 && !visaError && (
//                   <p className="text-center py-[24px] text-[#64748b] text-[14px] tracking-[-0.5px]">
//                     No visa types available. Please contact support.
//                   </p>
//                 )}
//               </div>
//             )}
//           </div>

//           {/* Section 3: Requirements */}
//           {selectedVisa && (
//             <div className="bg-white border border-[#f1f5f9] rounded-[16px]
//                             drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)] p-[25px] flex flex-col gap-[24px]">
//               <p className="text-[#0f172a] text-[18px] font-semibold tracking-[-0.5px] leading-[28px]">
//                 Requirements for {selectedVisa.code}
//               </p>
//               <p className="text-[#64748b] text-[14px] font-normal tracking-[-0.5px] leading-[20px] -mt-4">
//                 You will need to complete these steps in the following sections.
//               </p>

//               <div className="flex flex-col gap-[12px]">
//                 {(selectedVisa.requirements ?? []).length > 0 ? (
//                   (selectedVisa.requirements ?? []).map((req: string, i: number) => (
//                     <div
//                       key={i}
//                       className="bg-[rgba(248,250,252,0.5)] border border-[#f1f5f9] rounded-[12px]
//                                  flex items-center gap-[12px] h-[50px] pl-[13px] pr-[17px] py-[13px]"
//                     >
//                       <div className="bg-[#e2e8f0] flex items-center justify-center rounded-full shrink-0 size-[24px]">
//                         <img src={imgReqDot} alt="" className="w-[8.75px] h-[10px] object-contain" />
//                       </div>
//                       <span className="text-[#334155] text-[14px] font-medium tracking-[-0.5px] leading-[20px]">
//                         {req}
//                       </span>
//                     </div>
//                   ))
//                 ) : (
//                   <p className="text-[#94a3b8] text-[14px] tracking-[-0.5px]">
//                     No specific requirements listed for this visa type.
//                   </p>
//                 )}
//               </div>

//               <div className="flex flex-col gap-[6px]">
//                 <label className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">
//                   Additional Notes{" "}
//                   <span className="text-[#94a3b8] font-normal">(Optional)</span>
//                 </label>
//                 <textarea
//                   value={notes}
//                   onChange={e => setNotes(e.target.value)}
//                   placeholder="Any special instructions or notes..."
//                   rows={3}
//                   className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[12px] px-[17px] py-[11px]
//                              text-[#0f172a] text-[14px] font-normal tracking-[-0.5px] leading-[20px]
//                              resize-none focus:outline-none focus:border-[#3a46e5] transition-colors
//                              placeholder:text-[#94a3b8]"
//                   style={{ fontFamily: "Inter, sans-serif" }}
//                 />
//               </div>
//             </div>
//           )}

//           {/* Footer actions */}
//           <div className="border-t border-[#e2e8f0] flex items-center justify-between pt-[25px] pb-[48px]">

//             <button
//               type="button"
//               onClick={() => handleSubmit(true)}
//               disabled={loading}
//               className="flex items-center gap-[8px] text-[#64748b] text-[14px] font-medium
//                          tracking-[-0.5px] leading-[20px] hover:text-[#0f172a]
//                          transition-colors disabled:opacity-50"
//             >
//               <Save size={12} className="shrink-0" />
//               Save as Draft
//             </button>

//             <div className="flex items-center gap-[16px]">
//               <Link
//                 to="/applications"
//                 className="bg-[#f1f5f9] h-[40px] px-[24px] rounded-[12px] flex items-center
//                            text-[#334155] text-[14px] font-medium tracking-[-0.5px] leading-[20px]
//                            hover:bg-[#e2e8f0] transition-colors"
//               >
//                 Cancel
//               </Link>
//               <button
//                 type="button"
//                 onClick={() => handleSubmit(false)}
//                 disabled={loading || !selectedVisaId}
//                 className="h-[40px] px-[24px] rounded-[12px] flex items-center gap-[8px]
//                            text-white text-[14px] font-medium tracking-[-0.5px] leading-[20px]
//                            drop-shadow-[0px_1px_1px_rgba(0,0,0,0.05)]
//                            hover:opacity-90 transition-opacity disabled:opacity-60"
//                 style={{ backgroundImage: "linear-gradient(170.61deg, rgb(58,70,229) 0%, rgb(157,78,221) 100%)" }}
//               >
//                 {loading ? (
//                   <>
//                     <Loader2 size={14} className="animate-spin shrink-0" />
//                     Creating…
//                   </>
//                 ) : (
//                   <>
//                     Continue to Requirements
//                     <ArrowRight size={12} className="shrink-0" />
//                   </>
//                 )}
//               </button>
//             </div>
//           </div>

//         </div>
//       </main>
//     </div>
//   );
// }


// src/pages/employee/NewApplication.tsx
import { useState,useEffect} from "react";
import { useNavigate, Link } from "react-router-dom";
import { createApplication } from "../../api/employee/applications.api";

import { useCurrentUser } from "../../hooks/useAuth";
import { useVisaTypes } from "../../hooks/employee/useApplications";
import { Lock, Save, ArrowRight, Loader2 } from "lucide-react";
import type { AxiosError } from "axios";

// ── Assets ────────────────────────────────────────────────────────────────────
import imgCheckGreen  from "../../assets/icons/check-green.svg";
import imgRadioFilled from "../../assets/icons/radio-filled.svg";
import imgReqDot      from "../../assets/icons/req-dot.svg";
import { PageContent, PageHeader } from "../../components/layout/Pageheader";
// ─────────────────────────────────────────────────────────────────────────────
export default function NewApplication() {
  const navigate = useNavigate();

  const { data: user }                                                   = useCurrentUser();
  const { data: visaTypesRaw, isLoading: visaLoading, error: visaError } = useVisaTypes();
  const visaTypes = visaTypesRaw ?? [];

  // ── Form state ────────────────────────────────────────────────────────────
  const [selectedVisaId,  setSelectedVisaId]  = useState<string>("");
  const [sponsorEmployer, setSponsorEmployer] = useState("");
  const [notes,           setNotes]           = useState("");
  const [loading,         setLoading]         = useState(false);
  const [error,           setError]           = useState<string | null>(null);

  // Auto-select first visa type once loaded
  useEffect(() => {
    if (visaTypes.length > 0 && !selectedVisaId) {
      setSelectedVisaId(visaTypes[0].id);
    }
  }, [visaTypes.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedVisa = visaTypes.find(v => v.id === selectedVisaId);
  const fullName     = user ? `${user.first_name} ${user.last_name}` : "—";
  const email        = user?.email ?? "—";

  // ── Submit ────────────────────────────────────────────────────────────────
  async function handleSubmit(isDraft: boolean) {
    if (!selectedVisaId) { setError("Please select a visa type."); return; }
    setLoading(true);
    setError(null);
    try {
      const app = await createApplication({
        visa_type_id:     selectedVisaId,
        sponsor_employer: sponsorEmployer || undefined,
        notes:            notes || undefined,
      });
      if (!app?.id) {
        setError("Application created but ID missing. Please check your applications list.");
        return;
      }
      navigate(isDraft ? "/applications/list" : `/documents/upload?application_id=${app.id}`);
    } catch (e: unknown) {
      const err = e as AxiosError<{ detail: string }>;
      const httpStatus = err.response?.status;
      if (httpStatus === 409) {
        setError(
          err.response?.data?.detail ??
          "You already have a draft for this visa type. Please complete or delete it first."
        );
      } else {
        setError(
          err.response?.data?.detail ??
          (e instanceof Error ? e.message : "Something went wrong.")
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden" style={{ fontFamily: "Inter, sans-serif" }}>

      {/* TOP HEADER */}
      <PageHeader
        title="New Application"
        subtitle="Start your visa application"
        showBell
      />
      <PageContent>
        <div className="max-w-[1500px] mx-auto w-full flex flex-col gap-[24px]">

          <h1 className="text-[#0f172a] text-[24px] font-bold tracking-[-0.5px] leading-[32px] whitespace-nowrap">
            Create New Application
          </h1>

          {/* Step indicator */}
          <div className="bg-white border border-[#f1f5f9] rounded-[16px]
                          shadow-[0px_4px_12px_0px_rgba(0,0,0,0.02)]
                          flex items-center justify-between h-[54px] p-[17px] overflow-clip">

            <div className="flex items-center gap-[8px] px-[8px]">
              <div className="bg-[#ecfdf5] flex items-center justify-center rounded-full shrink-0 size-[20px]">
                <img src={imgCheckGreen} alt="" className="w-[8.75px] h-[10px] object-contain" />
              </div>
              <span className="text-[#059669] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
                Profile Check
              </span>
            </div>

            <div className="bg-[#e2e8f0] h-px w-[32px] shrink-0" />

            <div className="flex items-center gap-[8px] px-[8px]">
              <div className="bg-[#3a46e5] flex items-center justify-center rounded-full shrink-0 size-[20px]">
                <span className="text-white text-[12px] font-medium tracking-[-0.5px] leading-[16px]">2</span>
              </div>
              <span className="text-[#3a46e5] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
                Visa Type
              </span>
            </div>

            <div className="bg-[#e2e8f0] h-px w-[32px] shrink-0" />

            <div className="flex items-center gap-[8px] px-[8px] opacity-50">
              <div className="bg-[#f1f5f9] flex items-center justify-center rounded-full shrink-0 size-[20px]">
                <span className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">3</span>
              </div>
              <span className="text-[#64748b] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
                Requirements
              </span>
            </div>

            <div className="bg-[#e2e8f0] h-px w-[32px] shrink-0" />

            <div className="flex items-center gap-[8px] px-[8px] opacity-50">
              <div className="bg-[#f1f5f9] flex items-center justify-center rounded-full shrink-0 size-[20px]">
                <span className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">4</span>
              </div>
              <span className="text-[#64748b] text-[14px] font-medium tracking-[-0.5px] leading-[20px] whitespace-nowrap">
                Review
              </span>
            </div>
          </div>

          {/* Errors */}
          {(error || visaError) && (
            <div className="bg-[#fef2f2] border border-[#fca5a5] text-[#dc2626] rounded-[12px]
                            px-[16px] py-[12px] text-[14px] tracking-[-0.5px]">
              {error ?? visaError}
            </div>
          )}

          {/* Section 1: Applicant Information */}
          <div className="bg-white border border-[#f1f5f9] rounded-[16px]
                          drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)] p-[25px] flex flex-col gap-[24px]">

            <div className="flex items-center justify-between pb-[17px] border-b border-[#f1f5f9]">
              <p className="text-[#0f172a] text-[18px] font-semibold tracking-[-0.5px] leading-[28px]">
                Applicant Information
              </p>
              <span className="bg-[#f0f5ff] border border-[#e5edff] text-[#2f35ca] text-[12px]
                               font-medium tracking-[-0.5px] leading-[16px] px-[10px] py-[5px] rounded-[6px]">
                Prefilled
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-[16px] sm:gap-[24px]">

              <div className="flex flex-col gap-[6px]">
                <label className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">
                  Full Name
                </label>
                <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[12px] h-[42px]
                                flex items-center justify-between px-[17px] py-[11px]">
                  <span className="text-[#0f172a] text-[14px] font-normal tracking-[-0.5px] leading-[20px] truncate">
                    {fullName}
                  </span>
                  <Lock size={10} className="text-[#94a3b8] shrink-0 ml-2" />
                </div>
              </div>

              <div className="flex flex-col gap-[6px]">
                <label className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">
                  Email Address
                </label>
                <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[12px] h-[42px]
                                flex items-center justify-between px-[17px] py-[11px]">
                  <span className="text-[#0f172a] text-[14px] font-normal tracking-[-0.5px] leading-[20px] truncate">
                    {email}
                  </span>
                  <Lock size={10} className="text-[#94a3b8] shrink-0 ml-2" />
                </div>
              </div>

              {/* <div className="flex flex-col gap-[6px]">
                <label className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">
                  Current Nationality
                </label>
                <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[12px] h-[42px]
                                flex items-center justify-between px-[17px] py-[11px]">
                  <span className="text-[#0f172a] text-[14px] font-normal tracking-[-0.5px] leading-[20px]">
                    {fullName}
                  </span>
                  <Lock size={10} className="text-[#94a3b8] shrink-0 ml-2" />
                </div>
              </div> */}

              <div className="flex flex-col gap-[6px]">
                <label className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">
                  Sponsoring Employer
                </label>
                <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[12px] h-[42px]
                                flex items-center px-[17px] py-[11px]
                                focus-within:border-[#3a46e5] focus-within:ring-1
                                focus-within:ring-[#3a46e5] transition-colors">
                  <input
                    type="text"
                    value={sponsorEmployer}
                    onChange={e => setSponsorEmployer(e.target.value)}
                    placeholder="e.g. TechCorp Inc."
                    className="bg-transparent text-[#0f172a] text-[14px] font-normal tracking-[-0.5px]
                               leading-[20px] w-full focus:outline-none placeholder:text-[#94a3b8]"
                    style={{ fontFamily: "Inter, sans-serif" }}
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <Link
                to="/profile?returnTo=/applications/new"
                className="text-[#3a46e5] text-[14px] font-medium tracking-[-0.5px] leading-[20px] hover:underline"
              >
                Edit Profile Data
              </Link>
            </div>
          </div>

          {/* Section 2: Select Visa Type */}
          <div className="bg-white border border-[#f1f5f9] rounded-[16px]
                          drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)] p-[25px] flex flex-col gap-[24px]">
            <p className="text-[#0f172a] text-[18px] font-semibold tracking-[-0.5px] leading-[28px]">
              Select Visa Type
            </p>

            {visaLoading && (
              <div className="flex items-center justify-center py-[32px]">
                <Loader2 size={24} className="animate-spin text-[#3a46e5]" />
              </div>
            )}

            {!visaLoading && (
              <div className="flex flex-col gap-[16px]">
                {visaTypes.map(visa => {
                  const isSelected = selectedVisaId === visa.id;
                  return (
                    <label
                      key={visa.id}
                      onClick={() => setSelectedVisaId(visa.id)}
                      className={`flex gap-[12px] p-[17px] rounded-[12px] border cursor-pointer transition-colors ${
                        isSelected
                          ? "bg-[rgba(240,245,255,0.3)] border-[#5269f2]"
                          : "bg-white border-[#e2e8f0] hover:border-[#5269f2] hover:bg-[rgba(240,245,255,0.1)]"
                      }`}
                    >
                      <div className="flex items-start pt-[2px] shrink-0 w-[16px]">
                        {isSelected ? (
                          <div className="bg-white border-[0.5px] border-[#0075ff] rounded-full
                                          p-[2px] flex items-center justify-center shrink-0 size-[16px]">
                            <img src={imgRadioFilled} alt="" className="size-[12.8px] object-contain" />
                          </div>
                        ) : (
                          <div className="bg-white border-[0.5px] border-black rounded-full shrink-0 size-[16px]" />
                        )}
                      </div>
                      <div className="flex flex-col gap-[4px] flex-1 min-w-0">
                        <span className="text-[#0f172a] text-[14px] font-semibold tracking-[-0.5px] leading-[20px]">
                          {visa.name}
                        </span>
                        <span className="text-[#64748b] text-[12px] font-normal tracking-[-0.5px] leading-[16px]">
                          {visa.description}
                        </span>
                      </div>
                    </label>
                  );
                })}

                {visaTypes.length === 0 && !visaError && (
                  <p className="text-center py-[24px] text-[#64748b] text-[14px] tracking-[-0.5px]">
                    No visa types available. Please contact support.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Section 3: Requirements */}
          {selectedVisa && (
            <div className="bg-white border border-[#f1f5f9] rounded-[16px]
                            drop-shadow-[0px_4px_6px_rgba(0,0,0,0.02)] p-[25px] flex flex-col gap-[24px]">
              <p className="text-[#0f172a] text-[18px] font-semibold tracking-[-0.5px] leading-[28px]">
                Requirements for {selectedVisa.code}
              </p>
              <p className="text-[#64748b] text-[14px] font-normal tracking-[-0.5px] leading-[20px] -mt-4">
                You will need to complete these steps in the following sections.
              </p>

              <div className="flex flex-col gap-[12px]">
                {(selectedVisa.requirements ?? []).length > 0 ? (
                  (selectedVisa.requirements ?? []).map((req: string, i: number) => (
                    <div
                      key={i}
                      className="bg-[rgba(248,250,252,0.5)] border border-[#f1f5f9] rounded-[12px]
                                 flex items-center gap-[12px] h-[50px] pl-[13px] pr-[17px] py-[13px]"
                    >
                      <div className="bg-[#e2e8f0] flex items-center justify-center rounded-full shrink-0 size-[24px]">
                        <img src={imgReqDot} alt="" className="w-[8.75px] h-[10px] object-contain" />
                      </div>
                      <span className="text-[#334155] text-[14px] font-medium tracking-[-0.5px] leading-[20px]">
                        {req}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-[#94a3b8] text-[14px] tracking-[-0.5px]">
                    No specific requirements listed for this visa type.
                  </p>
                )}
              </div>

              <div className="flex flex-col gap-[6px]">
                <label className="text-[#64748b] text-[12px] font-medium tracking-[-0.5px] leading-[16px]">
                  Additional Notes{" "}
                  <span className="text-[#94a3b8] font-normal">(Optional)</span>
                </label>
                <textarea
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  placeholder="Any special instructions or notes..."
                  rows={3}
                  className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[12px] px-[17px] py-[11px]
                             text-[#0f172a] text-[14px] font-normal tracking-[-0.5px] leading-[20px]
                             resize-none focus:outline-none focus:border-[#3a46e5] transition-colors
                             placeholder:text-[#94a3b8]"
                  style={{ fontFamily: "Inter, sans-serif" }}
                />
              </div>
            </div>
          )}

          {/* Footer actions */}
          <div className="border-t border-[#e2e8f0] flex items-center justify-between pt-[25px] pb-[48px]">

            <button
              type="button"
              onClick={() => handleSubmit(true)}
              disabled={loading}
              className="flex items-center gap-[8px] text-[#64748b] text-[14px] font-medium
                         tracking-[-0.5px] leading-[20px] hover:text-[#0f172a]
                         transition-colors disabled:opacity-50"
            >
              <Save size={12} className="shrink-0" />
              Save as Draft
            </button>

            <div className="flex items-center gap-[16px]">
              <Link
                to="/applications"
                className="bg-[#f1f5f9] h-[40px] px-[24px] rounded-[12px] flex items-center
                           text-[#334155] text-[14px] font-medium tracking-[-0.5px] leading-[20px]
                           hover:bg-[#e2e8f0] transition-colors"
              >
                Cancel
              </Link>
              <button
                type="button"
                onClick={() => handleSubmit(false)}
                disabled={loading || !selectedVisaId}
                className="h-[40px] px-[24px] rounded-[12px] flex items-center gap-[8px]
                           text-white text-[14px] font-medium tracking-[-0.5px] leading-[20px]
                           drop-shadow-[0px_1px_1px_rgba(0,0,0,0.05)]
                           hover:opacity-90 transition-opacity disabled:opacity-60"
                style={{ backgroundImage: "linear-gradient(170.61deg, rgb(58,70,229) 0%, rgb(157,78,221) 100%)" }}
              >
                {loading ? (
                  <>
                    <Loader2 size={14} className="animate-spin shrink-0" />
                    Creating…
                  </>
                ) : (
                  <>
                    Continue to Requirements
                    <ArrowRight size={12} className="shrink-0" />
                  </>
                )}
              </button>
            </div>
          </div>

        </div>
      </PageContent>
    </div>
  );
}