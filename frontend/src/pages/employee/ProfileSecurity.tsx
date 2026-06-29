// // src/pages/employee/ProfileSecurity.tsx
// import { useState, useRef } from "react";
// import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
// import {
//   Edit2, Upload, Trash2, Save, RotateCcw,
//   CheckCircle, XCircle, Smartphone, Laptop, Tablet,
//   MapPin, Calendar, Wifi, EyeOff, Download,
//   Mail, Phone, Building, Globe2, Apple, AlertCircle,
//   Info, Check, X, FileText, Monitor, Clock, AlertTriangle,
//   Lock, Globe,
// } from "lucide-react";

// import { useMyProfile, useLoginHistory } from "../../hooks/useProfile";
// import { updateMyProfile, signOutAllDevices } from "../../api/profile.api";
// import { useAuthStore } from "../../store/authStore";
// import imgUserAvatar from "../../assets/icons/user-avatar.jpg";

// // ── Country codes ─────────────────────────────────────────────────────────────
// const COUNTRIES = [
//   { code: "US", flag: "🇺🇸", dial: "+1"   },
//   { code: "GB", flag: "🇬🇧", dial: "+44"  },
//   { code: "IN", flag: "🇮🇳", dial: "+91"  },
//   { code: "CA", flag: "🇨🇦", dial: "+1"   },
//   { code: "AU", flag: "🇦🇺", dial: "+61"  },
//   { code: "DE", flag: "🇩🇪", dial: "+49"  },
//   { code: "FR", flag: "🇫🇷", dial: "+33"  },
//   { code: "AE", flag: "🇦🇪", dial: "+971" },
//   { code: "SG", flag: "🇸🇬", dial: "+65"  },
//   { code: "JP", flag: "🇯🇵", dial: "+81"  },
//   { code: "CN", flag: "🇨🇳", dial: "+86"  },
//   { code: "BR", flag: "🇧🇷", dial: "+55"  },
//   { code: "MX", flag: "🇲🇽", dial: "+52"  },
//   { code: "ZA", flag: "🇿🇦", dial: "+27"  },
//   { code: "NG", flag: "🇳🇬", dial: "+234" },
// ];

// // ─── Types ────────────────────────────────────────────────────────────────────
// type SectionId =
//   | "profile"
//   | "authentication"
//   | "mfa"
//   | "login-history"
//   | "privacy"
//   | "devices"
//   | "session"
//   | "security-alerts";

// // ─── Toggle ──────────────────────────────────────────────────────────────────
// const Toggle = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => (
//   <button
//     onClick={onChange}
//     className={`relative inline-flex h-[24px] w-[44px] items-center rounded-full transition-colors duration-200 focus:outline-none ${
//       checked ? "bg-[#6366f1]" : "bg-[#e5e7eb]"
//     }`}
//   >
//     <span className={`inline-block h-[20px] w-[20px] transform rounded-full bg-white shadow-md transition-transform duration-200 ${
//       checked ? "translate-x-[22px]" : "translate-x-[2px]"
//     }`} />
//   </button>
// );

// // ─── Checkbox ─────────────────────────────────────────────────────────────────
// const Checkbox = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => (
//   <button
//     onClick={onChange}
//     className={`h-[18px] w-[18px] rounded border-[1.5px] flex items-center justify-center transition-colors ${
//       checked ? "bg-[#6366f1] border-[#6366f1]" : "bg-white border-[#d1d5db]"
//     }`}
//   >
//     {checked && <Check size={11} className="text-white" strokeWidth={3} />}
//   </button>
// );

// // ─── SectionCard ─────────────────────────────────────────────────────────────
// const SectionCard = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => (
//   <div className={`bg-white rounded-[16px] border border-[#e5e7eb] shadow-[0_1px_3px_rgba(0,0,0,0.06)] ${className}`}>
//     {children}
//   </div>
// );

// // ─── ReadOnlyField — grey locked box ─────────────────────────────────────────
// const ReadOnlyField = ({
//   label, value, hint,
// }: {
//   label: string; value: string; hint?: string;
// }) => (
//   <div className="flex flex-col gap-[6px]">
//     <label className="text-[13px] font-medium text-[#374151]">{label}</label>
//     <div className="w-full h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f3f4f6]
//                     text-[#9ca3af] text-[14px] px-[14px] flex items-center gap-[8px]
//                     cursor-not-allowed select-none">
//       <Lock size={12} className="text-[#d1d5db] shrink-0" />
//       <span className="truncate">{value || "—"}</span>
//     </div>
//     {hint && <p className="text-[11px] text-[#9ca3af]">{hint}</p>}
//   </div>
// );

// // // ─── EditableField ────────────────────────────────────────────────────────────
// // const EditableField = ({
// //   label, value, onChange, type = "text", hint, required = false,
// // }: {
// //   label: string; value: string; onChange: (v: string) => void;
// //   type?: string; hint?: string; required?: boolean;
// // }) => (
// //   <div className="flex flex-col gap-[6px]">
// //     <label className="text-[13px] font-medium text-[#374151]">
// //       {label}{required && <span className="text-[#ef4444] ml-[2px]">*</span>}
// //     </label>
// //     <input
// //       type={type}
// //       value={value}
// //       onChange={e => onChange(e.target.value)}
// //       className="w-full h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f9fafb]
// //                  text-[#111827] text-[14px] px-[14px] focus:outline-none focus:ring-2
// //                  focus:ring-[#6366f1] focus:border-transparent transition"
// //       style={{ fontFamily: "Inter, sans-serif" }}
// //     />
// //     {hint && <p className="text-[12px] text-[#6b7280]">{hint}</p>}
// //   </div>
// // );

// // ─── Section: Personal Information ───────────────────────────────────────────
// const PersonalInfoSection = () => {
//   const { data: profile, isLoading, refetch } = useMyProfile();
//   const user        = useAuthStore((s) => s.user);
//   const fileInputRef = useRef<HTMLInputElement>(null);

//   // ── Routing — return to caller page after save ────────────────────────────
//   const navigate     = useNavigate();
//   const [searchParams] = useSearchParams();

//   const [editing,     setEditing]     = useState(false);
//   const [saving,      setSaving]      = useState(false);
//   const [error,       setError]       = useState<string | null>(null);

//   // Only editable fields in state
//   const [phone,       setPhone]       = useState("");
//   const [countryCode, setCountryCode] = useState("+91");
//   const [timezone,    setTimezone]    = useState("PT");
//   const [language,    setLanguage]    = useState("en-US");

//   // Non-editable — derived from API / auth store
//   const displayName  = (profile?.full_legal_name?? `${user?.first_name ?? ""} ${user?.last_name ?? ""}`).trim()|| "—";
//   const displayEmail = user?.email ?? "—";
//   const displayTz    = profile?.timezone ?? "—";
//   const displayLang  = profile?.preferred_language ?? "—";
//   const displayPhone = profile?.phone_number
//     ? `${profile.country_code ?? ""} ${profile.phone_number}`.trim()
//     : "—";
//   const avatarUrl    = profile?.profile_picture_url ?? imgUserAvatar;

//   const seedForm = () => {
//     setPhone(profile?.phone_number ?? "");
//     setCountryCode(profile?.country_code ?? "+91");
//     setTimezone(profile?.timezone ?? "PT");
//     setLanguage(profile?.preferred_language ?? "en-US");
//   };

//   const handleEdit = () => {
//     seedForm();
//     setEditing(true);
//     setError(null);
//   };

//   const handleCancel = () => {
//     setEditing(false);
//     setError(null);
//   };

//   const handleSave = async () => {
//     setSaving(true);
//     setError(null);
//     try {
//       await updateMyProfile({
//         timezone:           timezone,
//         preferred_language: language,
//         phone_number: phone ? String(phone).trim() : undefined,
//         country_code:       countryCode || undefined,
//       });
//       await refetch();
//       setEditing(false);

//       // ── Navigate back to wherever the user came from (e.g. /applications/new)
//       const returnTo = searchParams.get("returnTo");
//       if (returnTo) {
//         navigate(returnTo);
//       }
//     } catch {
//       setError("Failed to save changes. Please try again.");
//     } finally {
//       setSaving(false);
//     }
//   };

//   if (isLoading) {
//     return (
//       <SectionCard>
//         <div className="flex items-center justify-center py-[64px]">
//           <svg className="w-7 h-7 animate-spin text-[#6366f1]" fill="none" viewBox="0 0 24 24">
//             <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
//             <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
//           </svg>
//         </div>
//       </SectionCard>
//     );
//   }

//   return (
//     <SectionCard>

//       {/* ── Header ── */}
//       <div className="p-[32px] border-b border-[#f3f4f6] flex items-center justify-between">
//         <div>
//           <h2 className="text-[20px] font-semibold text-[#111827]">Personal Information</h2>
//           <p className="text-[14px] text-[#6b7280] mt-[4px]">Update your contact details and preferences.</p>
//         </div>
//         {!editing && (
//           <button
//             onClick={handleEdit}
//             className="flex items-center gap-[6px] text-[#6366f1] text-[14px] font-medium hover:text-[#4f46e5] transition"
//           >
//             <Edit2 size={14} /> Edit
//           </button>
//         )}
//       </div>

//       {/* ── Error ── */}
//       {error && (
//         <div className="mx-[32px] mt-[16px] bg-[#fef2f2] border border-[#fca5a5] text-[#dc2626]
//                         rounded-[10px] px-[16px] py-[12px] text-[13px]">
//           {error}
//         </div>
//       )}

//       {/* ── Profile photo ── */}
//       <div className="px-[32px] py-[24px] border-b border-[#f3f4f6]">
//         <p className="text-[13px] font-medium text-[#374151] mb-[12px]">Profile Picture</p>
//         <div className="flex items-center gap-[20px]">
//           <div className="relative">
//             <img
//               src={avatarUrl}
//               alt="Profile"
//               className="w-[80px] h-[80px] rounded-full object-cover border-4 border-[#f3f4f6]"
//               onError={e => { (e.target as HTMLImageElement).src = imgUserAvatar; }}
//             />
//             <button
//               onClick={() => fileInputRef.current?.click()}
//               className="absolute bottom-0 right-0 w-[26px] h-[26px] bg-[#6366f1] rounded-full flex items-center justify-center"
//             >
//               <Upload size={12} className="text-white" />
//             </button>
//             <input ref={fileInputRef} type="file" accept="image/*" className="hidden" />
//           </div>
//           <div className="flex flex-col gap-[8px]">
//             <div className="flex gap-[8px]">
//               <button
//                 onClick={() => fileInputRef.current?.click()}
//                 className="flex items-center gap-[6px] px-[14px] h-[36px] bg-[#6366f1] text-white text-[13px] font-medium rounded-[8px] hover:bg-[#4f46e5] transition"
//               >
//                 <Upload size={13} /> Upload New
//               </button>
//               <button className="flex items-center gap-[6px] px-[14px] h-[36px] border border-[#e5e7eb] text-[#6b7280] text-[13px] font-medium rounded-[8px] hover:bg-[#f9fafb] transition">
//                 <Trash2 size={13} /> Remove
//               </button>
//             </div>
//             <p className="text-[12px] text-[#9ca3af]">JPG, PNG or GIF. Max size 5MB.</p>
//           </div>
//         </div>
//       </div>

//       {/* ── Fields ── */}
//       <div className="p-[32px] flex flex-col gap-[20px]">
//         {editing ? (
//           <>
//             {/* ── Name — NON-EDITABLE in edit mode ── */}
//             <div className="grid grid-cols-1 sm:grid-cols-2 gap-[20px]">
//               <ReadOnlyField
//                 label="Full Name"
//                 value={displayName}
//                 hint="Name cannot be changed here. Contact support to update."
//               />
//               <ReadOnlyField
//                 label="Email Address"
//                 value={displayEmail}
//                 hint="Email is used for login and cannot be changed here."
//               />
//             </div>

//             {/* ── Phone with country code ── */}
//             <div className="flex flex-col gap-[6px]">
//               <label className="text-[13px] font-medium text-[#374151]">Phone Number</label>
//               <div className="flex gap-[8px]">
//                 {/* Country code selector */}
//                 <select
//                   value={countryCode}
//                   onChange={e => setCountryCode(e.target.value)}
//                   className="h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f9fafb]
//                              text-[#111827] text-[14px] px-[10px] focus:outline-none
//                              focus:ring-2 focus:ring-[#6366f1] w-[110px] shrink-0 cursor-pointer"
//                   style={{ fontFamily: "Inter, sans-serif" }}
//                 >
//                   {COUNTRIES.map(c => (
//                     <option key={`${c.code}-${c.dial}`} value={c.dial}>
//                       {c.flag} {c.dial}
//                     </option>
//                   ))}
//                 </select>
//                 {/* Phone number input */}
//                 <input
//                   type="tel"
//                   value={phone}
//                   onChange={e => setPhone(String(e.target.value))}
//                   placeholder="9876543210"
//                   className="flex-1 h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f9fafb]
//                              text-[#111827] text-[14px] px-[14px] focus:outline-none
//                              focus:ring-2 focus:ring-[#6366f1] focus:border-transparent transition"
//                   style={{ fontFamily: "Inter, sans-serif" }}
//                 />
//               </div>
//               <p className="text-[12px] text-[#6b7280]">Used for SMS notifications and 2FA verification.</p>
//             </div>

//             {/* ── Timezone + Language ── */}
//             <div className="grid grid-cols-1 sm:grid-cols-2 gap-[20px]">
//               <div className="flex flex-col gap-[6px]">
//                 <label className="text-[13px] font-medium text-[#374151]">Timezone</label>
//                 <select
//                   value={timezone}
//                   onChange={e => setTimezone(e.target.value)}
//                   className="w-full h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f9fafb]
//                              text-[#111827] text-[14px] px-[14px] focus:outline-none
//                              focus:ring-2 focus:ring-[#6366f1] cursor-pointer"
//                   style={{ fontFamily: "Inter, sans-serif" }}
//                 >
//                   <option value="PT">Pacific Time (PT) - UTC-8</option>
//                   <option value="MT">Mountain Time (MT) - UTC-7</option>
//                   <option value="CT">Central Time (CT) - UTC-6</option>
//                   <option value="ET">Eastern Time (ET) - UTC-5</option>
//                   <option value="IST">India Standard Time (IST) - UTC+5:30</option>
//                   <option value="GMT">GMT - UTC+0</option>
//                   <option value="CET">Central European Time - UTC+1</option>
//                   <option value="SGT">Singapore Time - UTC+8</option>
//                   <option value="JST">Japan Standard Time - UTC+9</option>
//                   <option value="AEST">Australian Eastern - UTC+10</option>
//                 </select>
//               </div>
//               <div className="flex flex-col gap-[6px]">
//                 <label className="text-[13px] font-medium text-[#374151]">Preferred Language</label>
//                 <select
//                   value={language}
//                   onChange={e => setLanguage(e.target.value)}
//                   className="w-full h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f9fafb]
//                              text-[#111827] text-[14px] px-[14px] focus:outline-none
//                              focus:ring-2 focus:ring-[#6366f1] cursor-pointer"
//                   style={{ fontFamily: "Inter, sans-serif" }}
//                 >
//                   <option value="English">English (US)</option>
//                   <option value="es">Spanish</option>
//                   <option value="fr">French</option>
//                   <option value="de">German</option>
//                   <option value="hi">Hindi</option>
//                   <option value="zh">Chinese (Simplified)</option>
//                   <option value="ja">Japanese</option>
//                   <option value="ar">Arabic</option>
//                 </select>
//               </div>
//             </div>
//           </>
//         ) : (
//           /* ── Read-only view ── */
//           <div className="grid grid-cols-1 sm:grid-cols-2 gap-[20px]">
//             <div className="flex flex-col gap-[4px]">
//               <span className="text-[12px] text-[#6b7280] font-medium">Full Name</span>
//               <span className="text-[14px] text-[#111827]">{displayName}</span>
//             </div>
//             <div className="flex flex-col gap-[4px]">
//               <span className="text-[12px] text-[#6b7280] font-medium">Email Address</span>
//               <span className="text-[14px] text-[#111827]">{displayEmail}</span>
//             </div>
//             <div className="flex flex-col gap-[4px]">
//               <span className="text-[12px] text-[#6b7280] font-medium">Phone Number</span>
//               <span className="text-[14px] text-[#111827]">{displayPhone}</span>
//             </div>
//             <div className="flex flex-col gap-[4px]">
//               <span className="text-[12px] text-[#6b7280] font-medium">Timezone</span>
//               <span className="text-[14px] text-[#111827]">{displayTz}</span>
//             </div>
//             <div className="flex flex-col gap-[4px]">
//               <span className="text-[12px] text-[#6b7280] font-medium">Preferred Language</span>
//               <span className="text-[14px] text-[#111827]">{displayLang}</span>
//             </div>
//           </div>
//         )}
//       </div>

//       {/* ── Action buttons — edit mode only ── */}
//       {editing && (
//         <div className="px-[32px] pb-[28px] pt-[20px] border-t border-[#f3f4f6]
//                         flex items-center justify-between">
//           <button
//             onClick={handleCancel}
//             className="flex items-center gap-[6px] text-[#6b7280] text-[13px]
//                        hover:text-[#374151] transition"
//           >
//             <RotateCcw size={13} /> Undo Changes
//           </button>
//           <div className="flex gap-[8px]">
//             <button
//               onClick={handleCancel}
//               className="h-[40px] px-[20px] border border-[#e5e7eb] text-[#374151] text-[14px]
//                          font-medium rounded-[10px] hover:bg-[#f9fafb] transition"
//             >
//               Cancel
//             </button>
//             <button
//               onClick={handleSave}
//               disabled={saving}
//               className="h-[40px] px-[20px] bg-[#6366f1] text-white text-[14px] font-medium
//                          rounded-[10px] hover:bg-[#4f46e5] transition flex items-center
//                          gap-[6px] disabled:opacity-60"
//             >
//               <Save size={14} />
//               {saving ? "Saving…" : "Save Changes"}
//             </button>
//           </div>
//         </div>
//       )}
//     </SectionCard>
//   );
// };

// // ─── Section: Authentication Methods ─────────────────────────────────────────
// const AuthMethodCard = ({
//   icon, iconBg, title, description, features, buttonLabel, buttonVariant = "primary",
// }: {
//   icon: React.ReactNode; iconBg: string; title: string; description: string;
//   features: string[]; buttonLabel: string; buttonVariant?: "primary" | "outline";
// }) => (
//   <div className="border border-[#e5e7eb] rounded-[12px] p-[24px]">
//     <div className="flex items-start justify-between gap-[16px]">
//       <div className="flex items-start gap-[16px]">
//         <div className={`w-[48px] h-[48px] rounded-[12px] ${iconBg} flex items-center justify-center flex-shrink-0`}>{icon}</div>
//         <div>
//           <h3 className="text-[15px] font-semibold text-[#111827]">{title}</h3>
//           <p className="text-[13px] text-[#6b7280] mt-[4px]">{description}</p>
//           <ul className="mt-[10px] flex flex-wrap gap-[12px]">
//             {features.map((f) => (
//               <li key={f} className="flex items-center gap-[5px] text-[12px] text-[#6b7280]">
//                 <Check size={11} className="text-[#10b981]" strokeWidth={3} /> {f}
//               </li>
//             ))}
//           </ul>
//         </div>
//       </div>
//       <button className={`flex-shrink-0 h-[40px] px-[16px] text-[13px] font-medium rounded-[10px] transition whitespace-nowrap ${
//         buttonVariant === "primary" ? "bg-[#6366f1] text-white hover:bg-[#4f46e5]" : "border border-[#e5e7eb] text-[#374151] hover:bg-[#f9fafb]"
//       }`}>{buttonLabel}</button>
//     </div>
//   </div>
// );

// const AuthenticationSection = () => {
//   const user        = useAuthStore((s) => s.user);
//   const email = user?.email ?? "—";
//   return (
//     <SectionCard>
//       <div className="p-[32px] border-b border-[#f3f4f6]">
//         <h2 className="text-[20px] font-semibold text-[#111827]">Authentication Methods</h2>
//         <p className="text-[14px] text-[#6b7280] mt-[4px]">Configure how you log in to VisaFlow. We recommend enabling multiple authentication methods for added security.</p>
//       </div>
//       <div className="p-[32px] flex flex-col gap-[16px]">
//         <div className="border border-[#e5e7eb] rounded-[12px] p-[24px] bg-[#f9fafb]">
//           <div className="flex items-start justify-between gap-[16px]">
//             <div className="flex items-start gap-[16px]">
//               <div className="w-[48px] h-[48px] rounded-[12px] bg-[#e0e7ff] flex items-center justify-center flex-shrink-0">
//                 <Mail size={20} className="text-[#6366f1]" />
//               </div>
//               <div>
//                 <div className="flex items-center gap-[8px]">
//                   <h3 className="text-[15px] font-semibold text-[#111827]">Email & Password</h3>
//                   <span className="flex items-center gap-[4px] text-[12px] font-medium text-[#10b981] bg-[#d1fae5] px-[8px] py-[2px] rounded-full">
//                     <Check size={10} strokeWidth={3} /> Active
//                   </span>
//                 </div>
//                 <p className="text-[13px] text-[#6b7280] mt-[4px]">Primary login method using your email and password</p>
//                 <div className="mt-[8px] flex items-center gap-[6px] text-[13px] text-[#6b7280]">
//                   <Mail size={13} /> {email}
//                 </div>
//               </div>
//             </div>
//             <div className="flex gap-[8px] flex-shrink-0">
//               <button className="h-[36px] px-[14px] border border-[#e5e7eb] text-[#374151] text-[13px] font-medium rounded-[8px] hover:bg-white transition">Change Email</button>
//               <button className="h-[36px] px-[14px] border border-[#e5e7eb] text-[#374151] text-[13px] font-medium rounded-[8px] hover:bg-white transition">Change Password</button>
//             </div>
//           </div>
//         </div>
//         <AuthMethodCard icon={<Globe   size={20} className="text-[#ea4335]" />} iconBg="bg-[#fef2f2]" title="Google Authentication"   description="Sign in quickly using your Google account. No password required."     features={["One-click sign in","Automatic account recovery","Enhanced security with Google's 2FA"]} buttonLabel="Connect Google" />
//         <AuthMethodCard icon={<Monitor size={20} className="text-[#0078d4]" />} iconBg="bg-[#eff6ff]" title="Microsoft Authentication" description="Sign in with your Microsoft or Office 365 account."                     features={["Enterprise SSO integration","Works with Azure AD","Seamless Office 365 sync"]}          buttonLabel="Connect Microsoft" />
//         <AuthMethodCard icon={<Apple   size={20} className="text-[#374151]" />} iconBg="bg-[#f9fafb]" title="Apple Authentication"     description="Sign in with Apple ID with enhanced privacy protection."               features={["Privacy-focused authentication","Hide your email option","Built-in Face ID/Touch ID"]}  buttonLabel="Sign in with Apple" buttonVariant="outline" />
//       </div>
//     </SectionCard>
//   );
// };

// // ─── Section: MFA ─────────────────────────────────────────────────────────────
// const MFASection = () => (
//   <SectionCard>
//     <div className="p-[32px] border-b border-[#f3f4f6]">
//       <div className="flex items-center justify-between">
//         <h2 className="text-[20px] font-semibold text-[#111827]">Multi-Factor Authentication (2FA)</h2>
//         <span className="flex items-center gap-[6px] text-[13px] text-[#6b7280] bg-[#f3f4f6] px-[12px] py-[5px] rounded-full">
//           <XCircle size={14} className="text-[#ef4444]" /> Not Enabled
//         </span>
//       </div>
//       <p className="text-[14px] text-[#6b7280] mt-[4px]">Add an extra layer of security to your account by requiring a second verification method when signing in.</p>
//     </div>
//     <div className="p-[32px] flex flex-col gap-[16px]">
//       <div className="border-2 border-[#6366f1] rounded-[12px] p-[24px] bg-[#f5f3ff]">
//         <div className="flex items-start justify-between gap-[16px]">
//           <div className="flex items-start gap-[16px]">
//             <div className="w-[48px] h-[48px] rounded-[12px] bg-[#e0e7ff] flex items-center justify-center flex-shrink-0">
//               <Smartphone size={20} className="text-[#6366f1]" />
//             </div>
//             <div>
//               <div className="flex items-center gap-[8px]">
//                 <h3 className="text-[15px] font-semibold text-[#111827]">Authenticator App</h3>
//                 <span className="text-[11px] font-semibold text-[#6366f1] bg-[#e0e7ff] px-[8px] py-[2px] rounded-full">Recommended</span>
//               </div>
//               <p className="text-[13px] text-[#6b7280] mt-[4px]">Use apps like Google Authenticator, Authy, or Microsoft Authenticator to generate time-based codes.</p>
//               <ul className="mt-[10px] flex flex-wrap gap-[12px]">
//                 {["Most secure", "Works offline", "30-second codes"].map(f => (
//                   <li key={f} className="flex items-center gap-[5px] text-[12px] text-[#6b7280]">
//                     <Check size={11} className="text-[#10b981]" strokeWidth={3} /> {f}
//                   </li>
//                 ))}
//               </ul>
//             </div>
//           </div>
//           <button className="flex-shrink-0 h-[40px] px-[16px] bg-[#6366f1] text-white text-[13px] font-medium rounded-[10px] hover:bg-[#4f46e5] transition whitespace-nowrap">Setup Authenticator</button>
//         </div>
//       </div>
//       <div className="border border-[#e5e7eb] rounded-[12px] p-[24px]">
//         <div className="flex items-start justify-between gap-[16px]">
//           <div className="flex items-start gap-[16px]">
//             <div className="w-[48px] h-[48px] rounded-[12px] bg-[#f0fdf4] flex items-center justify-center flex-shrink-0">
//               <Phone size={20} className="text-[#10b981]" />
//             </div>
//             <div>
//               <h3 className="text-[15px] font-semibold text-[#111827]">SMS Text Message</h3>
//               <p className="text-[13px] text-[#6b7280] mt-[4px]">Receive verification codes via text message to your phone number.</p>
//               <ul className="mt-[10px] flex flex-wrap gap-[12px]">
//                 {["Easy to use", "No app required"].map(f => (
//                   <li key={f} className="flex items-center gap-[5px] text-[12px] text-[#6b7280]">
//                     <Check size={11} className="text-[#10b981]" strokeWidth={3} /> {f}
//                   </li>
//                 ))}
//                 <li className="flex items-center gap-[5px] text-[12px] text-[#6b7280]">
//                   <X size={11} className="text-[#ef4444]" strokeWidth={3} /> Requires cell signal
//                 </li>
//               </ul>
//             </div>
//           </div>
//           <button className="flex-shrink-0 h-[40px] px-[16px] bg-[#6366f1] text-white text-[13px] font-medium rounded-[10px] hover:bg-[#4f46e5] transition whitespace-nowrap">Add Phone Number</button>
//         </div>
//       </div>
//       <div className="border border-[#e5e7eb] rounded-[12px] p-[24px] opacity-60">
//         <div className="flex items-start justify-between gap-[16px]">
//           <div className="flex items-start gap-[16px]">
//             <div className="w-[48px] h-[48px] rounded-[12px] bg-[#fef3c7] flex items-center justify-center flex-shrink-0">
//               <FileText size={20} className="text-[#f59e0b]" />
//             </div>
//             <div>
//               <h3 className="text-[15px] font-semibold text-[#111827]">Backup Codes</h3>
//               <p className="text-[13px] text-[#6b7280] mt-[4px]">Generate one-time use backup codes in case you lose access to your primary 2FA method.</p>
//               <ul className="mt-[10px] flex flex-wrap gap-[12px]">
//                 {["Emergency access", "Print or save securely"].map(f => (
//                   <li key={f} className="flex items-center gap-[5px] text-[12px] text-[#6b7280]">
//                     <Check size={11} className="text-[#10b981]" strokeWidth={3} /> {f}
//                   </li>
//                 ))}
//                 <li className="flex items-center gap-[5px] text-[12px] text-[#6b7280]">
//                   <X size={11} className="text-[#ef4444]" strokeWidth={3} /> Single use only
//                 </li>
//               </ul>
//             </div>
//           </div>
//           <button disabled className="flex-shrink-0 h-[40px] px-[16px] border border-[#e5e7eb] text-[#9ca3af] text-[13px] font-medium rounded-[10px] cursor-not-allowed whitespace-nowrap">Enable 2FA First</button>
//         </div>
//       </div>
//     </div>
//   </SectionCard>
// );

// // ─── Section: Login History — real data ───────────────────────────────────────
// const LoginHistorySection = () => {
//   const { data: history, isLoading, error } = useLoginHistory(20);
//   const [signingOut, setSigningOut] = useState(false);

//   const deviceIcon = (type: string) => {
//     if (type === "mobile") return <Smartphone size={16} className="text-[#6366f1]" />;
//     if (type === "tablet") return <Tablet     size={16} className="text-[#6366f1]" />;
//     return                        <Laptop     size={16} className="text-[#6366f1]" />;
//   };

//   const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
//     success: { bg: "",             text: "",                label: ""        },
//     failed:  { bg: "bg-[#fee2e2]", text: "text-[#991b1b]", label: "Failed"  },
//     blocked: { bg: "bg-[#fee2e2]", text: "text-[#991b1b]", label: "Blocked" },
//   };

//   const handleSignOutAll = async () => {
//     setSigningOut(true);
//     try { await signOutAllDevices(); } finally { setSigningOut(false); }
//   };

//   return (
//     <SectionCard>
//       <div className="p-[32px] border-b border-[#f3f4f6] flex items-start justify-between">
//         <div>
//           <h2 className="text-[20px] font-semibold text-[#111827]">Login History</h2>
//           <p className="text-[14px] text-[#6b7280] mt-[4px] max-w-[520px]">Review recent access to your account. If you notice suspicious activity, change your password immediately.</p>
//         </div>
//         <button className="flex items-center gap-[6px] h-[40px] px-[16px] border border-[#e5e7eb] text-[#374151] text-[13px] font-medium rounded-[10px] hover:bg-[#f9fafb] transition whitespace-nowrap">
//           <Download size={14} /> Export Full History
//         </button>
//       </div>
//       <div className="p-[32px] flex flex-col gap-[12px]">
//         {isLoading && (
//           <div className="flex items-center justify-center py-[32px]">
//             <svg className="w-6 h-6 animate-spin text-[#6366f1]" fill="none" viewBox="0 0 24 24">
//               <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
//               <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
//             </svg>
//           </div>
//         )}
//         {error && <p className="text-[13px] text-[#ef4444] text-center py-[16px]">{error}</p>}
//         {!isLoading && !error && history.length === 0 && (
//           <p className="text-[13px] text-[#6b7280] text-center py-[16px]">No login history found.</p>
//         )}
//         {!isLoading && history.map(entry => {
//           const conf        = statusConfig[entry.status] ?? statusConfig.success;
//           const locationStr = [entry.city, entry.country].filter(Boolean).join(", ") || "Unknown location";
//           const deviceStr   = [entry.browser, entry.os].filter(Boolean).join(" on ")  || "Unknown device";
//           const dateStr     = new Date(entry.created_at).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
//           const isBad       = entry.status === "blocked" || entry.status === "failed";

//           return (
//             <div
//               key={entry.id}
//               className={`border rounded-[12px] p-[20px] ${
//                 isBad ? "border-[#fca5a5] bg-[#fff5f5]"
//                 : entry.is_current_session ? "border-[#6366f1] bg-[#f5f3ff]"
//                 : "border-[#e5e7eb]"
//               }`}
//             >
//               <div className="flex items-start justify-between">
//                 <div className="flex items-start gap-[14px]">
//                   <div className={`w-[40px] h-[40px] rounded-[10px] flex items-center justify-center flex-shrink-0 ${
//                     isBad ? "bg-[#fee2e2]" : "bg-[#f0fdf4]"
//                   }`}>
//                     {isBad
//                       ? <AlertTriangle size={16} className="text-[#ef4444]" />
//                       : deviceIcon(entry.device_type)}
//                   </div>
//                   <div>
//                     <div className="flex items-center gap-[8px]">
//                       <p className="text-[14px] font-semibold text-[#111827]">
//                         {entry.is_current_session ? "Current Session"
//                           : isBad ? "Failed Login Attempt"
//                           : "Successful Login"}
//                       </p>
//                       {entry.is_current_session && (
//                         <span className="text-[11px] font-medium px-[8px] py-[2px] rounded-full bg-[#d1fae5] text-[#065f46]">Active Now</span>
//                       )}
//                       {conf.label && (
//                         <span className={`text-[11px] font-medium px-[8px] py-[2px] rounded-full ${conf.bg} ${conf.text}`}>{conf.label}</span>
//                       )}
//                     </div>
//                     <div className="mt-[8px] flex flex-col gap-[4px]">
//                       <div className="flex items-center gap-[6px] text-[12px] text-[#6b7280]"><Monitor  size={12} /> {deviceStr}</div>
//                       <div className="flex items-center gap-[6px] text-[12px] text-[#6b7280]"><MapPin   size={12} /> {locationStr}</div>
//                       <div className="flex items-center gap-[6px] text-[12px] text-[#6b7280]"><Calendar size={12} /> {dateStr}</div>
//                       {entry.ip_address && <div className="flex items-center gap-[6px] text-[12px] text-[#6b7280]"><Wifi size={12} /> IP: {entry.ip_address}</div>}
//                       {entry.failure_reason && <div className="flex items-center gap-[6px] text-[12px] text-[#ef4444]"><AlertCircle size={12} /> {entry.failure_reason}</div>}
//                     </div>
//                   </div>
//                 </div>
//                 {entry.status === "blocked"
//                   ? <button className="text-[13px] text-[#ef4444] font-medium hover:underline">Report</button>
//                   : !entry.is_current_session
//                   ? <button className="text-[#6b7280] hover:text-[#374151] transition"><EyeOff size={16} /></button>
//                   : null}
//               </div>
//             </div>
//           );
//         })}
//       </div>
//       <div className="mx-[32px] mb-[28px] bg-[#fffbeb] border border-[#fde68a] rounded-[10px] px-[20px] py-[16px] flex items-center justify-between">
//         <div className="flex items-start gap-[10px]">
//           <AlertTriangle size={18} className="text-[#f59e0b] flex-shrink-0 mt-[1px]" />
//           <div>
//             <p className="text-[13px] font-semibold text-[#92400e]">Security Tip</p>
//             <p className="text-[12px] text-[#92400e] mt-[2px]">Regularly review your login history and revoke access from unrecognized devices.</p>
//           </div>
//         </div>
//         <button
//           onClick={handleSignOutAll}
//           disabled={signingOut}
//           className="flex-shrink-0 h-[36px] px-[14px] border border-[#fde68a] text-[#92400e] text-[12px] font-medium rounded-[8px] hover:bg-[#fef3c7] transition whitespace-nowrap disabled:opacity-60"
//         >
//           {signingOut ? "Signing out…" : "Sign Out All Devices"}
//         </button>
//       </div>
//     </SectionCard>
//   );
// };

// // ─── Section: Privacy Settings ────────────────────────────────────────────────
// const ToggleRow = ({ title, description, checked, onChange }: {
//   title: string; description: string; checked: boolean; onChange: () => void;
// }) => (
//   <div className="flex items-center justify-between py-[18px] border-b border-[#f3f4f6] last:border-0">
//     <div>
//       <p className="text-[14px] font-medium text-[#111827]">{title}</p>
//       <p className="text-[12px] text-[#6b7280] mt-[2px]">{description}</p>
//     </div>
//     <Toggle checked={checked} onChange={onChange} />
//   </div>
// );

// const PrivacySection = () => {
//   const [toggles, setToggles] = useState({
//     email: true, phone: false, employment: true, visa: false,
//     analytics: true, updates: true, marketing: false,
//     autoShareEmployer: true, autoShareLawyer: true, requireApproval: false,
//   });
//   const toggle = (key: keyof typeof toggles) => setToggles(p => ({ ...p, [key]: !p[key] }));

//   return (
//     <div className="flex flex-col gap-[20px]">
//       <SectionCard>
//         <div className="p-[28px] border-b border-[#f3f4f6]">
//           <div className="flex items-center justify-between">
//             <div>
//               <h3 className="text-[17px] font-semibold text-[#111827]">Profile Visibility</h3>
//               <p className="text-[13px] text-[#6b7280] mt-[2px]">Choose who can view your profile information and contact details.</p>
//             </div>
//             <select className="h-[36px] px-[12px] border border-[#e5e7eb] rounded-[8px] text-[13px] text-[#374151] bg-white focus:outline-none focus:ring-2 focus:ring-[#6366f1]"
//               style={{ fontFamily: "Inter, sans-serif" }}>
//               <option>Team Members Only</option><option>All Users</option><option>Private</option>
//             </select>
//           </div>
//         </div>
//         <div className="px-[28px] py-[8px] grid grid-cols-2 gap-[4px]">
//           {[
//             { key: "email"      as const, label: "Email Address",  icon: <Mail     size={14} /> },
//             { key: "phone"      as const, label: "Phone Number",   icon: <Phone    size={14} /> },
//             { key: "employment" as const, label: "Employment Info", icon: <Building size={14} /> },
//             { key: "visa"       as const, label: "Visa Status",    icon: <FileText size={14} /> },
//           ].map(({ key, label, icon }) => (
//             <div key={key} className="flex items-center justify-between py-[14px] px-[16px] rounded-[8px] hover:bg-[#f9fafb]">
//               <div className="flex items-center gap-[8px] text-[13px] text-[#374151]">
//                 <span className="text-[#6b7280]">{icon}</span> {label}
//               </div>
//               <Toggle checked={toggles[key]} onChange={() => toggle(key)} />
//             </div>
//           ))}
//         </div>
//       </SectionCard>
//       <SectionCard>
//         <div className="p-[28px] border-b border-[#f3f4f6]">
//           <h3 className="text-[17px] font-semibold text-[#111827]">Data Sharing & Analytics</h3>
//           <p className="text-[13px] text-[#6b7280] mt-[2px]">Help us improve VisaFlow by sharing anonymous usage data.</p>
//         </div>
//         <div className="px-[28px]">
//           <ToggleRow title="Usage Analytics"          description="Share anonymous data about how you use VisaFlow to help us improve features and performance." checked={toggles.analytics} onChange={() => toggle("analytics")} />
//           <ToggleRow title="Product Updates & Tips"   description="Receive personalized tips and feature updates based on your usage patterns."                  checked={toggles.updates}   onChange={() => toggle("updates")}   />
//           <ToggleRow title="Marketing Communications" description="Receive promotional emails about new features, webinars, and special offers."                  checked={toggles.marketing} onChange={() => toggle("marketing")} />
//         </div>
//       </SectionCard>
//       <SectionCard>
//         <div className="p-[28px] border-b border-[#f3f4f6]">
//           <h3 className="text-[17px] font-semibold text-[#111827]">Document Access Control</h3>
//           <p className="text-[13px] text-[#6b7280] mt-[2px]">Manage default sharing settings for your immigration documents.</p>
//         </div>
//         <div className="px-[28px]">
//           <ToggleRow title="Auto-share with Employer"              description="Automatically grant your employer access to case-related documents."                    checked={toggles.autoShareEmployer} onChange={() => toggle("autoShareEmployer")} />
//           <ToggleRow title="Auto-share with Lawyer"                description="Automatically grant your immigration lawyer access to all case documents."              checked={toggles.autoShareLawyer}   onChange={() => toggle("autoShareLawyer")}   />
//           <ToggleRow title="Require Approval for External Sharing" description="Get notified when someone wants to share your documents outside your organization."     checked={toggles.requireApproval}   onChange={() => toggle("requireApproval")}   />
//         </div>
//       </SectionCard>
//       <SectionCard>
//         <div className="p-[28px] border-b border-[#f3f4f6]">
//           <h3 className="text-[17px] font-semibold text-[#111827]">Data Retention & Deletion</h3>
//           <p className="text-[13px] text-[#6b7280] mt-[2px]">Manage how long your data is stored and request permanent deletion.</p>
//         </div>
//         <div className="p-[28px] flex flex-col gap-[16px]">
//           <div className="bg-[#eff6ff] border border-[#bfdbfe] rounded-[10px] p-[20px] flex items-start gap-[12px]">
//             <Info size={16} className="text-[#3b82f6] flex-shrink-0 mt-[2px]" />
//             <div>
//               <p className="text-[13px] font-semibold text-[#1e40af]">Data Retention Policy</p>
//               <p className="text-[12px] text-[#1e40af] mt-[4px]">Your case data is retained for 7 years after case completion to comply with immigration record-keeping requirements.</p>
//               <button className="text-[12px] text-[#3b82f6] font-medium mt-[8px] hover:underline">Learn more about our data retention policy</button>
//             </div>
//           </div>
//           <div className="flex items-center justify-between p-[16px] border border-[#e5e7eb] rounded-[10px]">
//             <div>
//               <p className="text-[13px] font-semibold text-[#111827]">Download Your Data</p>
//               <p className="text-[12px] text-[#6b7280] mt-[2px]">Export all your personal information and documents in a portable format.</p>
//             </div>
//             <button className="flex items-center gap-[6px] h-[36px] px-[14px] border border-[#e5e7eb] text-[#374151] text-[13px] font-medium rounded-[8px] hover:bg-[#f9fafb] transition">
//               <Download size={13} /> Request Export
//             </button>
//           </div>
//           <div className="flex items-center justify-between p-[16px] border border-[#fca5a5] rounded-[10px] bg-[#fff5f5]">
//             <div>
//               <p className="text-[13px] font-semibold text-[#991b1b]">Delete My Account</p>
//               <p className="text-[12px] text-[#ef4444] mt-[2px]">Permanently delete your account and all associated data. This action cannot be undone.</p>
//             </div>
//             <button className="flex items-center gap-[6px] h-[36px] px-[14px] bg-[#ef4444] text-white text-[13px] font-medium rounded-[8px] hover:bg-[#dc2626] transition">
//               <Trash2 size={13} /> Delete Account
//             </button>
//           </div>
//         </div>
//       </SectionCard>
//     </div>
//   );
// };

// // ─── Section: Connected Devices ───────────────────────────────────────────────
// const DeviceCard = ({ icon, name, isCurrent, browser, os, lastActive, location }: {
//   icon: React.ReactNode; name: string; isCurrent?: boolean;
//   browser: string; os: string; lastActive: string; location: string;
// }) => (
//   <div className={`border rounded-[12px] p-[20px] ${isCurrent ? "border-[#6366f1] bg-[#f5f3ff]" : "border-[#e5e7eb]"}`}>
//     <div className="flex items-start justify-between">
//       <div className="flex items-start gap-[14px]">
//         <div className={`w-[48px] h-[48px] rounded-[12px] flex items-center justify-center flex-shrink-0 ${isCurrent ? "bg-[#e0e7ff]" : "bg-[#f3f4f6]"}`}>
//           {icon}
//         </div>
//         <div>
//           <div className="flex items-center gap-[8px]">
//             <p className="text-[14px] font-semibold text-[#111827]">{name}</p>
//             {isCurrent && <span className="text-[11px] font-medium text-[#6366f1] bg-[#e0e7ff] px-[8px] py-[2px] rounded-full">Current Device</span>}
//           </div>
//           <div className="mt-[8px] flex flex-col gap-[4px]">
//             <div className="flex items-center gap-[6px] text-[12px] text-[#6b7280]"><Globe2  size={12} /> {browser}</div>
//             <div className="flex items-center gap-[6px] text-[12px] text-[#6b7280]"><Monitor size={12} /> {os}</div>
//             <div className="flex items-center gap-[6px] text-[12px] text-[#6b7280]"><Clock   size={12} /> {lastActive}</div>
//             <div className="flex items-center gap-[6px] text-[12px] text-[#6b7280]"><MapPin  size={12} /> {location}</div>
//           </div>
//         </div>
//       </div>
//       {!isCurrent && (
//         <button className="h-[36px] px-[14px] border border-[#e5e7eb] text-[#374151] text-[13px] font-medium rounded-[8px] hover:bg-[#f9fafb] transition whitespace-nowrap">Revoke Access</button>
//       )}
//     </div>
//   </div>
// );

// const ConnectedDevicesSection = () => (
//   <SectionCard>
//     <div className="p-[32px] border-b border-[#f3f4f6] flex items-start justify-between">
//       <div>
//         <h2 className="text-[20px] font-semibold text-[#111827]">Connected Devices</h2>
//         <p className="text-[14px] text-[#6b7280] mt-[4px] max-w-[520px]">Manage devices that have access to your VisaFlow account. Revoke access from devices you no longer use.</p>
//       </div>
//       <span className="text-[13px] font-medium text-[#6366f1] bg-[#e0e7ff] px-[12px] py-[6px] rounded-full whitespace-nowrap">4 Active Devices</span>
//     </div>
//     <div className="p-[32px] flex flex-col gap-[12px]">
//       <DeviceCard icon={<Laptop     size={22} className="text-[#6366f1]" />} name='MacBook Pro 16"'              isCurrent browser="Chrome 120.0.6099.129" os="macOS Sonoma 14.2"  lastActive="Last active: Just now"    location="San Francisco, CA" />
//       <DeviceCard icon={<Smartphone size={22} className="text-[#374151]" />} name="iPhone 14 Pro"                          browser="Safari (Mobile)"         os="iOS 17.2"           lastActive="Last active: 2 hours ago" location="San Francisco, CA" />
//       <DeviceCard icon={<Tablet     size={22} className="text-[#374151]" />} name="iPad Air"                               browser="Chrome (Mobile)"         os="iPadOS 17.2"        lastActive="Last active: 1 day ago"   location="San Francisco, CA" />
//       <DeviceCard icon={<Laptop     size={22} className="text-[#374151]" />} name='Work Laptop (MacBook Pro 14")' browser="Chrome 119.0.6045.199"  os="macOS Ventura 13.6" lastActive="Last active: 3 days ago"  location="San Francisco, CA" />
//     </div>
//     <div className="mx-[32px] mb-[28px] bg-[#fef3c7] border border-[#fde68a] rounded-[10px] px-[20px] py-[16px] flex items-center justify-between">
//       <div className="flex items-start gap-[10px]">
//         <AlertTriangle size={18} className="text-[#f59e0b] flex-shrink-0 mt-[1px]" />
//         <div>
//           <p className="text-[13px] font-semibold text-[#92400e]">Suspicious Activity Detected?</p>
//           <p className="text-[12px] text-[#92400e] mt-[2px]">If you see a device you don't recognize, revoke its access immediately and change your password.</p>
//         </div>
//       </div>
//       <button className="flex-shrink-0 h-[36px] px-[14px] bg-[#f59e0b] text-white text-[12px] font-medium rounded-[8px] hover:bg-[#d97706] transition whitespace-nowrap">Sign Out All Devices</button>
//     </div>
//   </SectionCard>
// );

// // ─── Section: Session Settings ────────────────────────────────────────────────
// const SessionSection = () => {
//   const [rememberMe, setRememberMe] = useState(true);
//   const [concurrent, setConcurrent] = useState(true);
//   return (
//     <SectionCard>
//       <div className="p-[32px] border-b border-[#f3f4f6]">
//         <h2 className="text-[20px] font-semibold text-[#111827]">Session Settings</h2>
//         <p className="text-[14px] text-[#6b7280] mt-[4px]">Configure how long you stay signed in and when your session expires.</p>
//       </div>
//       <div className="p-[32px] flex flex-col gap-[24px]">
//         <div className="border border-[#e5e7eb] rounded-[12px] p-[24px]">
//           <div className="flex items-start justify-between gap-[16px]">
//             <div>
//               <h3 className="text-[15px] font-semibold text-[#111827]">Automatic Sign Out</h3>
//               <p className="text-[13px] text-[#6b7280] mt-[2px]">Choose when to automatically sign out after inactivity for security.</p>
//             </div>
//             <select className="h-[36px] px-[12px] border border-[#e5e7eb] rounded-[8px] text-[13px] text-[#374151] bg-[#f9fafb] focus:outline-none focus:ring-2 focus:ring-[#6366f1]"
//               style={{ fontFamily: "Inter, sans-serif" }}>
//               <option>15 minutes</option><option>30 minutes</option><option>1 hour</option><option>4 hours</option>
//             </select>
//           </div>
//           <div className="mt-[16px] flex items-start gap-[8px] bg-[#eff6ff] rounded-[8px] px-[14px] py-[12px]">
//             <Info size={14} className="text-[#3b82f6] flex-shrink-0 mt-[1px]" />
//             <p className="text-[12px] text-[#1e40af]">We recommend setting a timeout of 1 hour or less when accessing VisaFlow from shared or public computers.</p>
//           </div>
//         </div>
//         <div className="border border-[#e5e7eb] rounded-[12px] p-[24px]">
//           <div className="flex items-start justify-between">
//             <div className="flex-1 mr-[24px]">
//               <h3 className="text-[15px] font-semibold text-[#111827]">Remember Me</h3>
//               <p className="text-[13px] text-[#6b7280] mt-[4px]">Stay signed in on this device for 30 days without requiring login credentials.</p>
//               <p className="mt-[8px] flex items-center gap-[5px] text-[12px] text-[#6b7280]">
//                 <AlertCircle size={12} className="text-[#f59e0b]" /> This setting only applies to your current device
//               </p>
//             </div>
//             <Toggle checked={rememberMe} onChange={() => setRememberMe(!rememberMe)} />
//           </div>
//         </div>
//         <div className="border border-[#e5e7eb] rounded-[12px] p-[24px]">
//           <div className="flex items-start justify-between">
//             <div className="flex-1 mr-[24px]">
//               <h3 className="text-[15px] font-semibold text-[#111827]">Concurrent Sessions</h3>
//               <p className="text-[13px] text-[#6b7280] mt-[4px]">Allow multiple active sessions on different devices simultaneously.</p>
//               <div className="mt-[16px] border border-[#e5e7eb] rounded-[8px] overflow-hidden">
//                 <div className="flex items-center justify-between px-[16px] py-[12px] border-b border-[#f3f4f6]">
//                   <span className="text-[13px] text-[#6b7280]">Maximum concurrent sessions:</span>
//                   <span className="text-[18px] font-bold text-[#111827]">5</span>
//                 </div>
//                 <div className="flex items-center justify-between px-[16px] py-[12px]">
//                   <span className="text-[13px] text-[#6b7280]">Currently active:</span>
//                   <span className="text-[18px] font-bold text-[#6366f1]">4</span>
//                 </div>
//               </div>
//             </div>
//             <Toggle checked={concurrent} onChange={() => setConcurrent(!concurrent)} />
//           </div>
//         </div>
//       </div>
//     </SectionCard>
//   );
// };

// // ─── Section: Security Alerts ─────────────────────────────────────────────────
// const AlertRow = ({ title, description, emailChecked, smsChecked, onEmailChange, onSmsChange }: {
//   title: string; description: string; emailChecked: boolean; smsChecked: boolean;
//   onEmailChange: () => void; onSmsChange: () => void;
// }) => (
//   <div className="flex items-center justify-between py-[18px] border-b border-[#f3f4f6] last:border-0 gap-[16px]">
//     <div className="flex-1">
//       <p className="text-[14px] font-medium text-[#111827]">{title}</p>
//       <p className="text-[12px] text-[#6b7280] mt-[2px]">{description}</p>
//     </div>
//     <div className="flex items-center gap-[16px] flex-shrink-0">
//       <label className="flex items-center gap-[6px] cursor-pointer">
//         <Checkbox checked={emailChecked} onChange={onEmailChange} />
//         <span className="text-[12px] text-[#6b7280]">Email</span>
//       </label>
//       <label className="flex items-center gap-[6px] cursor-pointer">
//         <Checkbox checked={smsChecked} onChange={onSmsChange} />
//         <span className="text-[12px] text-[#6b7280]">SMS</span>
//       </label>
//     </div>
//   </div>
// );

// const SecurityAlertsSection = () => {
//   const [alerts, setAlerts] = useState({
//     newDevice:        { email: true,  sms: true  },
//     failedLogin:      { email: true,  sms: true  },
//     passwordChanged:  { email: true,  sms: false },
//     settingsModified: { email: true,  sms: false },
//     unusualActivity:  { email: true,  sms: true  },
//   });
//   type AlertKey = keyof typeof alerts;
//   const toggle = (key: AlertKey, ch: "email" | "sms") =>
//     setAlerts(p => ({ ...p, [key]: { ...p[key], [ch]: !p[key][ch] } }));

//   return (
//     <SectionCard>
//       <div className="p-[32px] border-b border-[#f3f4f6]">
//         <h2 className="text-[20px] font-semibold text-[#111827]">Security Alerts & Notifications</h2>
//         <p className="text-[14px] text-[#6b7280] mt-[4px]">Get notified about important security events related to your account.</p>
//       </div>
//       <div className="px-[32px]">
//         <AlertRow title="New Device Login"           description="Get alerted when your account is accessed from a new device or location."              emailChecked={alerts.newDevice.email}        smsChecked={alerts.newDevice.sms}        onEmailChange={() => toggle("newDevice",        "email")} onSmsChange={() => toggle("newDevice",        "sms")} />
//         <AlertRow title="Failed Login Attempts"      description="Receive notifications when someone fails to log in to your account multiple times."     emailChecked={alerts.failedLogin.email}      smsChecked={alerts.failedLogin.sms}      onEmailChange={() => toggle("failedLogin",      "email")} onSmsChange={() => toggle("failedLogin",      "sms")} />
//         <AlertRow title="Password Changed"           description="Get notified immediately when your password is changed."                                emailChecked={alerts.passwordChanged.email}  smsChecked={alerts.passwordChanged.sms}  onEmailChange={() => toggle("passwordChanged",  "email")} onSmsChange={() => toggle("passwordChanged",  "sms")} />
//         <AlertRow title="Security Settings Modified" description="Be alerted when 2FA, authentication methods, or privacy settings are changed."          emailChecked={alerts.settingsModified.email} smsChecked={alerts.settingsModified.sms} onEmailChange={() => toggle("settingsModified", "email")} onSmsChange={() => toggle("settingsModified", "sms")} />
//         <AlertRow title="Unusual Activity Detected"  description="Get alerts when our system detects suspicious behavior or potential security threats."   emailChecked={alerts.unusualActivity.email}  smsChecked={alerts.unusualActivity.sms}  onEmailChange={() => toggle("unusualActivity",  "email")} onSmsChange={() => toggle("unusualActivity",  "sms")} />
//       </div>
//       <div className="mx-[32px] mb-[28px] mt-[8px] bg-[#f0fdf4] border border-[#bbf7d0] rounded-[10px] px-[20px] py-[16px]">
//         <div className="flex items-start gap-[10px]">
//           <CheckCircle size={18} className="text-[#10b981] flex-shrink-0 mt-[1px]" />
//           <div>
//             <p className="text-[13px] font-semibold text-[#065f46]">Your Account is Secure</p>
//             <p className="text-[12px] text-[#065f46] mt-[2px]">All recommended security features are enabled. Keep these settings active to protect your sensitive immigration data.</p>
//           </div>
//         </div>
//       </div>
//     </SectionCard>
//   );
// };

// // ─── Section titles ───────────────────────────────────────────────────────────
// const SECTION_TITLES: Record<SectionId, { title: string; subtitle: string }> = {
//   profile:           { title: "Profile & Security",               subtitle: "Manage your account settings and security preferences" },
//   authentication:    { title: "Authentication Methods",           subtitle: "Configure how you log in to VisaFlow and connect external accounts." },
//   mfa:               { title: "Multi-Factor Authentication",      subtitle: "Add an extra layer of security to your account." },
//   "login-history":   { title: "Login History",                    subtitle: "Review recent access to your account and manage active sessions." },
//   privacy:           { title: "Privacy Settings",                 subtitle: "Control who can see your information and how your data is used." },
//   devices:           { title: "Connected Devices",                subtitle: "Manage all devices that have access to your VisaFlow account." },
//   session:           { title: "Session Settings",                 subtitle: "Configure how long you stay signed in and session expiry behavior." },
//   "security-alerts": { title: "Security Alerts & Notifications",  subtitle: "Get notified about important security events related to your account." },
// };

// // ─── Main Page ────────────────────────────────────────────────────────────────
// export default function ProfileSecurity() {
//   const location = useLocation();

//   const getSection = (): SectionId => {
//     const path = location.pathname;
//     if (path === "/profile/authentication")  return "authentication";
//     if (path === "/profile/mfa")             return "mfa";
//     if (path === "/profile/login-history")   return "login-history";
//     if (path === "/profile/privacy")         return "privacy";
//     if (path === "/profile/devices")         return "devices";
//     if (path === "/profile/session")         return "session";
//     if (path === "/profile/security-alerts") return "security-alerts";
//     return "profile";
//   };

//   const activeSection = getSection();
//   const { title, subtitle } = SECTION_TITLES[activeSection];

//   const SECTION_COMPONENTS: Record<SectionId, React.ReactNode> = {
//     profile:           <PersonalInfoSection />,
//     authentication:    <AuthenticationSection />,
//     mfa:               <MFASection />,
//     "login-history":   <LoginHistorySection />,
//     privacy:           <PrivacySection />,
//     devices:           <ConnectedDevicesSection />,
//     session:           <SessionSection />,
//     "security-alerts": <SecurityAlertsSection />,
//   };

//   return (
//     <div className="flex flex-col flex-1 min-h-0 overflow-hidden bg-[#f9fafb]"
//          style={{ fontFamily: "Inter, sans-serif" }}>
//       <header className="bg-white border-b border-[#f1f5f9] flex h-[72px] items-center px-[32px] shrink-0 sticky top-0 z-10">
//         <div className="flex flex-col gap-[2px]">
//           <p className="font-bold text-[#0f172a] text-[20px] tracking-[-0.5px] leading-[28px]">{title}</p>
//           <p className="text-[#64748b] text-[12px] tracking-[-0.5px] leading-[16px]">{subtitle}</p>
//         </div>
//       </header>
//       <main className="flex-1 overflow-y-auto p-[40px]">
//         <div className="max-w-[900px]">
//           {SECTION_COMPONENTS[activeSection]}
//         </div>
//       </main>
//     </div>
//   );
// }

// src/pages/employee/ProfileSecurity.tsx
import { useState, useRef } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  Edit2, Upload, Trash2, Save, RotateCcw,
  CheckCircle, XCircle, Smartphone, Laptop, Tablet,
  MapPin, Calendar, Wifi, EyeOff, Download,
  Mail, Phone, Building, Globe2, Apple, 
  Info, Check, X, FileText, Monitor, Clock, AlertTriangle,
  Lock, Globe,
} from "lucide-react";

import { useMyProfile, useLoginHistory } from "../../hooks/employee/useProfile";
import { updateMyProfile, signOutAllDevices, uploadProfilePicture } from "../../api/employee/profile.api";
import { useAuthStore } from "../../store/authStore";
import imgUserAvatar from "../../assets/icons/user-avatar.jpg";
import { getFileUrl } from "../../utils/fileUrl";
import { updateUiSessionProfile } from '../../utils/uiSession';
import { PageHeader, PageContent } from "../../components/layout/Pageheader";

// ── Country codes ─────────────────────────────────────────────────────────────
const COUNTRIES = [
  { code: "US", flag: "🇺🇸", dial: "+1"   },
  { code: "GB", flag: "🇬🇧", dial: "+44"  },
  { code: "IN", flag: "🇮🇳", dial: "+91"  },
  { code: "CA", flag: "🇨🇦", dial: "+1"   },
  { code: "AU", flag: "🇦🇺", dial: "+61"  },
  { code: "DE", flag: "🇩🇪", dial: "+49"  },
  { code: "FR", flag: "🇫🇷", dial: "+33"  },
  { code: "AE", flag: "🇦🇪", dial: "+971" },
  { code: "SG", flag: "🇸🇬", dial: "+65"  },
  { code: "JP", flag: "🇯🇵", dial: "+81"  },
  { code: "CN", flag: "🇨🇳", dial: "+86"  },
  { code: "BR", flag: "🇧🇷", dial: "+55"  },
  { code: "MX", flag: "🇲🇽", dial: "+52"  },
  { code: "ZA", flag: "🇿🇦", dial: "+27"  },
  { code: "NG", flag: "🇳🇬", dial: "+234" },
];

// ─── Types ────────────────────────────────────────────────────────────────────
type SectionId =
  | "profile" | "authentication" | "mfa" | "login-history"
  | "privacy"  | "devices"        | "session" | "security-alerts";

// ─── Shared small components ──────────────────────────────────────────────────
const Toggle = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => (
  <button onClick={onChange}
    className={`relative inline-flex h-[24px] w-[44px] items-center rounded-full transition-colors duration-200 focus:outline-none flex-shrink-0 ${checked ? "bg-[#6366f1]" : "bg-[#e5e7eb]"}`}>
    <span className={`inline-block h-[20px] w-[20px] transform rounded-full bg-white shadow-md transition-transform duration-200 ${checked ? "translate-x-[22px]" : "translate-x-[2px]"}`} />
  </button>
);

const Checkbox = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => (
  <button onClick={onChange}
    className={`h-[18px] w-[18px] rounded border-[1.5px] flex items-center justify-center transition-colors flex-shrink-0 ${checked ? "bg-[#6366f1] border-[#6366f1]" : "bg-white border-[#d1d5db]"}`}>
    {checked && <Check size={11} className="text-white" strokeWidth={3} />}
  </button>
);

const SectionCard = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => (
  <div className={`bg-white rounded-[16px] border border-[#e5e7eb] shadow-[0_1px_3px_rgba(0,0,0,0.06)] ${className}`}>
    {children}
  </div>
);

const ReadOnlyField = ({ label, value, hint }: { label: string; value: string; hint?: string }) => (
  <div className="flex flex-col gap-[6px]">
    <label className="text-[13px] font-medium text-[#374151]">{label}</label>
    <div className="w-full h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f3f4f6]
                    text-[#9ca3af] text-[14px] px-[14px] flex items-center gap-[8px]
                    cursor-not-allowed select-none">
      <Lock size={12} className="text-[#d1d5db] shrink-0" />
      <span className="truncate">{value || "—"}</span>
    </div>
    {hint && <p className="text-[11px] text-[#9ca3af]">{hint}</p>}
  </div>
);

const Spinner = ({ size = 13, className = "text-white" }: { size?: number; className?: string }) => (
  <svg className={`animate-spin ${className}`} style={{ width: size, height: size }} fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
  </svg>
);

// ─── Card/section inner padding helper ───────────────────────────────────────
// Use this everywhere instead of hardcoded p-[32px]
const cardPad = "p-[20px] sm:p-[24px] lg:p-[32px]";
const cardPadX = "px-[20px] sm:px-[24px] lg:px-[32px]";

// ─── Section: Personal Information ───────────────────────────────────────────
const PersonalInfoSection = () => {
  const { data: profile, isLoading, refetch } = useMyProfile();
  const user         = useAuthStore((s) => s.user);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate     = useNavigate();
  const [searchParams] = useSearchParams();

  const [editing,        setEditing]        = useState(false);
  const [saving,         setSaving]         = useState(false);
  const [error,          setError]          = useState<string | null>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarError,     setAvatarError]     = useState<string | null>(null);
  const [phone,       setPhone]       = useState("");
  const [countryCode, setCountryCode] = useState("+91");
  const [timezone,    setTimezone]    = useState("PT");
  const [language,    setLanguage]    = useState("en-US");

  const displayName  = (profile?.full_legal_name ?? `${user?.first_name ?? ""} ${user?.last_name ?? ""}`).trim() || "—";
  const displayEmail = user?.email ?? "—";
  const displayTz    = profile?.timezone ?? "—";
  const displayLang  = profile?.preferred_language ?? "—";
  const displayPhone = profile?.phone_number ? `${profile.country_code ?? ""} ${profile.phone_number}`.trim() : "—";
  const avatarUrl    = getFileUrl(profile?.profile_picture_url) ?? imgUserAvatar;

  const seedForm = () => {
    setPhone(profile?.phone_number ?? "");
    setCountryCode(profile?.country_code ?? "+91");
    setTimezone(profile?.timezone ?? "PT");
    setLanguage(profile?.preferred_language ?? "en-US");
  };

  const handleEdit = () => { seedForm(); setEditing(true); setError(null); };
  const handleCancel = () => { setEditing(false); setError(null); };

  const handleSave = async () => {
    setSaving(true); setError(null);
    try {
      await updateMyProfile({ timezone, preferred_language: language, phone_number: phone ? String(phone).trim() : undefined, country_code: countryCode || undefined });
      await refetch();
      setEditing(false);
      const returnTo = searchParams.get("returnTo");
      if (returnTo) navigate(returnTo);
    } catch { setError("Failed to save changes. Please try again."); }
    finally { setSaving(false); }
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { setAvatarError("File must be under 5 MB."); return; }
    setAvatarUploading(true); setAvatarError(null);
    try {
      const result = await uploadProfilePicture(file);
      await refetch();
      if (result?.profile_picture_url) updateUiSessionProfile(result.profile_picture_url);
    } catch { setAvatarError("Failed to upload photo. Please try again."); }
    finally { setAvatarUploading(false); e.target.value = ""; }
  };

  if (isLoading) return <SectionCard><div className="flex items-center justify-center py-[64px]"><Spinner size={28} className="text-[#6366f1]" /></div></SectionCard>;

  return (
    <SectionCard>
      {/* Header */}
      <div className={`${cardPad} border-b border-[#f3f4f6] flex items-center justify-between gap-[12px]`}>
        <div>
          <h2 className="text-[17px] sm:text-[20px] font-semibold text-[#111827]">Personal Information</h2>
          <p className="text-[13px] sm:text-[14px] text-[#6b7280] mt-[4px]">Update your contact details and preferences.</p>
        </div>
        {!editing && (
          <button onClick={handleEdit} className="flex items-center gap-[6px] text-[#6366f1] text-[13px] sm:text-[14px] font-medium hover:text-[#4f46e5] transition flex-shrink-0">
            <Edit2 size={14} /> Edit
          </button>
        )}
      </div>

      {error && <div className={`${cardPadX} mt-[16px] bg-[#fef2f2] border border-[#fca5a5] text-[#dc2626] rounded-[10px] px-[16px] py-[12px] text-[13px]`}>{error}</div>}

      {/* Profile photo */}
      <div className={`${cardPadX} py-[20px] sm:py-[24px] border-b border-[#f3f4f6]`}>
        <p className="text-[13px] font-medium text-[#374151] mb-[12px]">Profile Picture</p>
        <div className="flex flex-wrap items-center gap-[16px] sm:gap-[20px]">
          <div className="relative shrink-0">
            <img src={avatarUrl} alt="Profile"
              className="w-[64px] h-[64px] sm:w-[80px] sm:h-[80px] rounded-full object-cover border-4 border-[#f3f4f6]"
              onError={e => { (e.target as HTMLImageElement).src = imgUserAvatar; }} />
            <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/gif,image/webp" className="hidden" onChange={handleAvatarChange} />
          </div>
          <div className="flex flex-col gap-[8px]">
            <div className="flex flex-wrap gap-[8px]">
              <button onClick={() => fileInputRef.current?.click()} disabled={avatarUploading}
                className="flex items-center gap-[6px] px-[12px] sm:px-[14px] h-[34px] sm:h-[36px] bg-[#6366f1] text-white text-[12px] sm:text-[13px] font-medium rounded-[8px] hover:bg-[#4f46e5] transition disabled:opacity-60">
                {avatarUploading ? <><Spinner size={13} /> Uploading…</> : <><Upload size={13} /> Upload New</>}
              </button>
              <button className="flex items-center gap-[6px] px-[12px] sm:px-[14px] h-[34px] sm:h-[36px] border border-[#e5e7eb] text-[#6b7280] text-[12px] sm:text-[13px] font-medium rounded-[8px] hover:bg-[#f9fafb] transition">
                <Trash2 size={13} /> Remove
              </button>
            </div>
            {avatarError ? <p className="text-[12px] text-[#ef4444]">{avatarError}</p>
              : <p className="text-[12px] text-[#9ca3af]">JPG, PNG, GIF or WebP. Max size 5 MB.</p>}
          </div>
        </div>
      </div>

      {/* Fields */}
      <div className={`${cardPad} flex flex-col gap-[16px] sm:gap-[20px]`}>
        {editing ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-[16px] sm:gap-[20px]">
              <ReadOnlyField label="Full Name" value={displayName} hint="Name cannot be changed here. Contact support to update." />
              <ReadOnlyField label="Email Address" value={displayEmail} hint="Email is used for login and cannot be changed here." />
            </div>
            <div className="flex flex-col gap-[6px]">
              <label className="text-[13px] font-medium text-[#374151]">Phone Number</label>
              <div className="flex gap-[8px]">
                <select value={countryCode} onChange={e => setCountryCode(e.target.value)}
                  className="h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f9fafb] text-[#111827] text-[14px] px-[10px] focus:outline-none focus:ring-2 focus:ring-[#6366f1] w-[100px] sm:w-[110px] shrink-0 cursor-pointer">
                  {COUNTRIES.map(c => <option key={`${c.code}-${c.dial}`} value={c.dial}>{c.flag} {c.dial}</option>)}
                </select>
                <input type="tel" value={phone} onChange={e => setPhone(String(e.target.value))} placeholder="9876543210"
                  className="flex-1 h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f9fafb] text-[#111827] text-[14px] px-[14px] focus:outline-none focus:ring-2 focus:ring-[#6366f1] focus:border-transparent transition" />
              </div>
              <p className="text-[12px] text-[#6b7280]">Used for SMS notifications and 2FA verification.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-[16px] sm:gap-[20px]">
              <div className="flex flex-col gap-[6px]">
                <label className="text-[13px] font-medium text-[#374151]">Timezone</label>
                <select value={timezone} onChange={e => setTimezone(e.target.value)}
                  className="w-full h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f9fafb] text-[#111827] text-[14px] px-[14px] focus:outline-none focus:ring-2 focus:ring-[#6366f1] cursor-pointer">
                  <option value="PT">Pacific Time (PT)</option><option value="MT">Mountain Time (MT)</option>
                  <option value="CT">Central Time (CT)</option><option value="ET">Eastern Time (ET)</option>
                  <option value="IST">India Standard Time (IST)</option><option value="GMT">GMT</option>
                  <option value="CET">Central European Time</option><option value="SGT">Singapore Time</option>
                  <option value="JST">Japan Standard Time</option><option value="AEST">Australian Eastern</option>
                </select>
              </div>
              <div className="flex flex-col gap-[6px]">
                <label className="text-[13px] font-medium text-[#374151]">Preferred Language</label>
                <select value={language} onChange={e => setLanguage(e.target.value)}
                  className="w-full h-[46px] rounded-[10px] border border-[#e5e7eb] bg-[#f9fafb] text-[#111827] text-[14px] px-[14px] focus:outline-none focus:ring-2 focus:ring-[#6366f1] cursor-pointer">
                  <option value="English">English (US)</option><option value="es">Spanish</option>
                  <option value="fr">French</option><option value="de">German</option>
                  <option value="hi">Hindi</option><option value="zh">Chinese (Simplified)</option>
                  <option value="ja">Japanese</option><option value="ar">Arabic</option>
                </select>
              </div>
            </div>
          </>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-[16px] sm:gap-[20px]">
            {[
              { label: "Full Name",           value: displayName  },
              { label: "Email Address",        value: displayEmail },
              { label: "Phone Number",         value: displayPhone },
              { label: "Timezone",             value: displayTz    },
              { label: "Preferred Language",   value: displayLang  },
            ].map(({ label, value }) => (
              <div key={label} className="flex flex-col gap-[4px]">
                <span className="text-[12px] text-[#6b7280] font-medium">{label}</span>
                <span className="text-[13px] sm:text-[14px] text-[#111827]">{value}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {editing && (
        <div className={`${cardPadX} pb-[20px] sm:pb-[28px] pt-[16px] sm:pt-[20px] border-t border-[#f3f4f6] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-[12px]`}>
          <button onClick={handleCancel} className="flex items-center justify-center sm:justify-start gap-[6px] text-[#6b7280] text-[13px] hover:text-[#374151] transition">
            <RotateCcw size={13} /> Undo Changes
          </button>
          <div className="flex gap-[8px]">
            <button onClick={handleCancel} className="flex-1 sm:flex-none h-[40px] px-[16px] sm:px-[20px] border border-[#e5e7eb] text-[#374151] text-[13px] sm:text-[14px] font-medium rounded-[10px] hover:bg-[#f9fafb] transition">
              Cancel
            </button>
            <button onClick={handleSave} disabled={saving}
              className="flex-1 sm:flex-none h-[40px] px-[16px] sm:px-[20px] bg-[#6366f1] text-white text-[13px] sm:text-[14px] font-medium rounded-[10px] hover:bg-[#4f46e5] transition flex items-center justify-center gap-[6px] disabled:opacity-60">
              {saving ? <><Spinner size={14} /> Saving…</> : <><Save size={14} /> Save Changes</>}
            </button>
          </div>
        </div>
      )}
    </SectionCard>
  );
};

// ─── Section: Authentication Methods ─────────────────────────────────────────
const AuthMethodCard = ({ icon, iconBg, title, description, features, buttonLabel, buttonVariant = "primary" }: {
  icon: React.ReactNode; iconBg: string; title: string; description: string;
  features: string[]; buttonLabel: string; buttonVariant?: "primary" | "outline";
}) => (
  <div className="border border-[#e5e7eb] rounded-[12px] p-[16px] sm:p-[24px]">
    <div className="flex flex-col sm:flex-row items-start gap-[12px] sm:gap-[16px]">
      <div className="flex items-start gap-[12px] sm:gap-[16px] flex-1 min-w-0">
        <div className={`w-[44px] h-[44px] sm:w-[48px] sm:h-[48px] rounded-[12px] ${iconBg} flex items-center justify-center flex-shrink-0`}>{icon}</div>
        <div className="min-w-0">
          <h3 className="text-[14px] sm:text-[15px] font-semibold text-[#111827]">{title}</h3>
          <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[4px]">{description}</p>
          <ul className="mt-[8px] sm:mt-[10px] flex flex-wrap gap-[8px] sm:gap-[12px]">
            {features.map(f => (
              <li key={f} className="flex items-center gap-[5px] text-[11px] sm:text-[12px] text-[#6b7280]">
                <Check size={11} className="text-[#10b981]" strokeWidth={3} /> {f}
              </li>
            ))}
          </ul>
        </div>
      </div>
      <button className={`w-full sm:w-auto flex-shrink-0 h-[38px] sm:h-[40px] px-[14px] sm:px-[16px] text-[12px] sm:text-[13px] font-medium rounded-[10px] transition whitespace-nowrap ${
        buttonVariant === "primary" ? "bg-[#6366f1] text-white hover:bg-[#4f46e5]" : "border border-[#e5e7eb] text-[#374151] hover:bg-[#f9fafb]"
      }`}>{buttonLabel}</button>
    </div>
  </div>
);

const AuthenticationSection = () => {
  const user  = useAuthStore((s) => s.user);
  const email = user?.email ?? "—";
  return (
    <SectionCard>
      <div className={`${cardPad} border-b border-[#f3f4f6]`}>
        <h2 className="text-[17px] sm:text-[20px] font-semibold text-[#111827]">Authentication Methods</h2>
        <p className="text-[13px] sm:text-[14px] text-[#6b7280] mt-[4px]">Configure how you log in to VisaFlow. We recommend enabling multiple authentication methods for added security.</p>
      </div>
      <div className={`${cardPad} flex flex-col gap-[12px] sm:gap-[16px]`}>
        <div className="border border-[#e5e7eb] rounded-[12px] p-[16px] sm:p-[24px] bg-[#f9fafb]">
          <div className="flex flex-col sm:flex-row items-start gap-[12px] sm:gap-[16px]">
            <div className="flex items-start gap-[12px] sm:gap-[16px] flex-1 min-w-0">
              <div className="w-[44px] h-[44px] sm:w-[48px] sm:h-[48px] rounded-[12px] bg-[#e0e7ff] flex items-center justify-center flex-shrink-0"><Mail size={20} className="text-[#6366f1]" /></div>
              <div className="min-w-0">
                <div className="flex items-center gap-[8px] flex-wrap">
                  <h3 className="text-[14px] sm:text-[15px] font-semibold text-[#111827]">Email & Password</h3>
                  <span className="flex items-center gap-[4px] text-[11px] sm:text-[12px] font-medium text-[#10b981] bg-[#d1fae5] px-[8px] py-[2px] rounded-full">
                    <Check size={10} strokeWidth={3} /> Active
                  </span>
                </div>
                <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[4px]">Primary login method using your email and password</p>
                <div className="mt-[8px] flex items-center gap-[6px] text-[12px] sm:text-[13px] text-[#6b7280]"><Mail size={13} /> {email}</div>
              </div>
            </div>
            <div className="flex gap-[8px] flex-wrap w-full sm:w-auto">
              <button className="flex-1 sm:flex-none h-[34px] sm:h-[36px] px-[12px] sm:px-[14px] border border-[#e5e7eb] text-[#374151] text-[12px] sm:text-[13px] font-medium rounded-[8px] hover:bg-white transition whitespace-nowrap">Change Email</button>
              <button className="flex-1 sm:flex-none h-[34px] sm:h-[36px] px-[12px] sm:px-[14px] border border-[#e5e7eb] text-[#374151] text-[12px] sm:text-[13px] font-medium rounded-[8px] hover:bg-white transition whitespace-nowrap">Change Password</button>
            </div>
          </div>
        </div>
        <AuthMethodCard icon={<Globe   size={20} className="text-[#ea4335]" />} iconBg="bg-[#fef2f2]" title="Google Authentication"   description="Sign in quickly using your Google account."          features={["One-click sign in","Automatic recovery","Google's 2FA"]}         buttonLabel="Connect Google" />
        <AuthMethodCard icon={<Monitor size={20} className="text-[#0078d4]" />} iconBg="bg-[#eff6ff]" title="Microsoft Authentication" description="Sign in with your Microsoft or Office 365 account."  features={["Enterprise SSO","Azure AD","Office 365 sync"]}                 buttonLabel="Connect Microsoft" />
        <AuthMethodCard icon={<Apple   size={20} className="text-[#374151]" />} iconBg="bg-[#f9fafb]" title="Apple Authentication"     description="Sign in with Apple ID with enhanced privacy."       features={["Privacy-focused","Hide your email","Face ID/Touch ID"]}       buttonLabel="Sign in with Apple" buttonVariant="outline" />
      </div>
    </SectionCard>
  );
};

// ─── Section: MFA ─────────────────────────────────────────────────────────────
const MFASection = () => (
  <SectionCard>
    <div className={`${cardPad} border-b border-[#f3f4f6]`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-[8px]">
        <h2 className="text-[17px] sm:text-[20px] font-semibold text-[#111827]">Multi-Factor Authentication (2FA)</h2>
        <span className="flex items-center gap-[6px] text-[12px] sm:text-[13px] text-[#6b7280] bg-[#f3f4f6] px-[12px] py-[5px] rounded-full w-fit">
          <XCircle size={14} className="text-[#ef4444]" /> Not Enabled
        </span>
      </div>
      <p className="text-[13px] sm:text-[14px] text-[#6b7280] mt-[4px]">Add an extra layer of security to your account by requiring a second verification method.</p>
    </div>
    <div className={`${cardPad} flex flex-col gap-[12px] sm:gap-[16px]`}>
      {/* Recommended option */}
      <div className="border-2 border-[#6366f1] rounded-[12px] p-[16px] sm:p-[24px] bg-[#f5f3ff]">
        <div className="flex flex-col sm:flex-row items-start gap-[12px] sm:gap-[16px]">
          <div className="flex items-start gap-[12px] flex-1 min-w-0">
            <div className="w-[44px] h-[44px] rounded-[12px] bg-[#e0e7ff] flex items-center justify-center flex-shrink-0"><Smartphone size={20} className="text-[#6366f1]" /></div>
            <div className="min-w-0">
              <div className="flex items-center gap-[8px] flex-wrap">
                <h3 className="text-[14px] sm:text-[15px] font-semibold text-[#111827]">Authenticator App</h3>
                <span className="text-[11px] font-semibold text-[#6366f1] bg-[#e0e7ff] px-[8px] py-[2px] rounded-full">Recommended</span>
              </div>
              <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[4px]">Use apps like Google Authenticator, Authy, or Microsoft Authenticator.</p>
              <ul className="mt-[8px] flex flex-wrap gap-[8px]">
                {["Most secure","Works offline","30-second codes"].map(f => (
                  <li key={f} className="flex items-center gap-[5px] text-[11px] sm:text-[12px] text-[#6b7280]">
                    <Check size={11} className="text-[#10b981]" strokeWidth={3} /> {f}
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <button className="w-full sm:w-auto flex-shrink-0 h-[38px] px-[14px] bg-[#6366f1] text-white text-[12px] sm:text-[13px] font-medium rounded-[10px] hover:bg-[#4f46e5] transition whitespace-nowrap">Setup Authenticator</button>
        </div>
      </div>
      {/* SMS option */}
      <div className="border border-[#e5e7eb] rounded-[12px] p-[16px] sm:p-[24px]">
        <div className="flex flex-col sm:flex-row items-start gap-[12px] sm:gap-[16px]">
          <div className="flex items-start gap-[12px] flex-1 min-w-0">
            <div className="w-[44px] h-[44px] rounded-[12px] bg-[#f0fdf4] flex items-center justify-center flex-shrink-0"><Phone size={20} className="text-[#10b981]" /></div>
            <div className="min-w-0">
              <h3 className="text-[14px] sm:text-[15px] font-semibold text-[#111827]">SMS Text Message</h3>
              <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[4px]">Receive verification codes via text message.</p>
              <ul className="mt-[8px] flex flex-wrap gap-[8px]">
                {[{ ok: true, t: "Easy to use" }, { ok: true, t: "No app required" }, { ok: false, t: "Requires cell signal" }].map(({ ok, t }) => (
                  <li key={t} className="flex items-center gap-[5px] text-[11px] sm:text-[12px] text-[#6b7280]">
                    {ok ? <Check size={11} className="text-[#10b981]" strokeWidth={3} /> : <X size={11} className="text-[#ef4444]" strokeWidth={3} />} {t}
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <button className="w-full sm:w-auto flex-shrink-0 h-[38px] px-[14px] bg-[#6366f1] text-white text-[12px] sm:text-[13px] font-medium rounded-[10px] hover:bg-[#4f46e5] transition whitespace-nowrap">Add Phone Number</button>
        </div>
      </div>
      {/* Backup codes — disabled */}
      <div className="border border-[#e5e7eb] rounded-[12px] p-[16px] sm:p-[24px] opacity-60">
        <div className="flex flex-col sm:flex-row items-start gap-[12px] sm:gap-[16px]">
          <div className="flex items-start gap-[12px] flex-1 min-w-0">
            <div className="w-[44px] h-[44px] rounded-[12px] bg-[#fef3c7] flex items-center justify-center flex-shrink-0"><FileText size={20} className="text-[#f59e0b]" /></div>
            <div className="min-w-0">
              <h3 className="text-[14px] sm:text-[15px] font-semibold text-[#111827]">Backup Codes</h3>
              <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[4px]">One-time use backup codes in case you lose access to your primary 2FA method.</p>
            </div>
          </div>
          <button disabled className="w-full sm:w-auto flex-shrink-0 h-[38px] px-[14px] border border-[#e5e7eb] text-[#9ca3af] text-[12px] sm:text-[13px] font-medium rounded-[10px] cursor-not-allowed whitespace-nowrap">Enable 2FA First</button>
        </div>
      </div>
    </div>
  </SectionCard>
);

// ─── Section: Login History ───────────────────────────────────────────────────
const LoginHistorySection = () => {
  const { data: history, isLoading, error } = useLoginHistory(20);
  const [signingOut, setSigningOut] = useState(false);

  const deviceIcon = (type: string) => {
    if (type === "mobile") return <Smartphone size={16} className="text-[#6366f1]" />;
    if (type === "tablet") return <Tablet     size={16} className="text-[#6366f1]" />;
    return                        <Laptop     size={16} className="text-[#6366f1]" />;
  };

  const handleSignOutAll = async () => {
    setSigningOut(true);
    try { await signOutAllDevices(); } finally { setSigningOut(false); }
  };

  return (
    <SectionCard>
      <div className={`${cardPad} border-b border-[#f3f4f6] flex flex-col sm:flex-row sm:items-start justify-between gap-[12px]`}>
        <div>
          <h2 className="text-[17px] sm:text-[20px] font-semibold text-[#111827]">Login History</h2>
          <p className="text-[13px] sm:text-[14px] text-[#6b7280] mt-[4px]">Review recent access to your account. If you notice suspicious activity, change your password immediately.</p>
        </div>
        <button className="flex items-center gap-[6px] h-[38px] sm:h-[40px] px-[14px] sm:px-[16px] border border-[#e5e7eb] text-[#374151] text-[12px] sm:text-[13px] font-medium rounded-[10px] hover:bg-[#f9fafb] transition whitespace-nowrap flex-shrink-0">
          <Download size={14} /> Export History
        </button>
      </div>
      <div className={`${cardPad} flex flex-col gap-[10px] sm:gap-[12px]`}>
        {isLoading && <div className="flex items-center justify-center py-[32px]"><Spinner size={24} className="text-[#6366f1]" /></div>}
        {error && <p className="text-[13px] text-[#ef4444] text-center py-[16px]">{error}</p>}
        {!isLoading && !error && history.length === 0 && <p className="text-[13px] text-[#6b7280] text-center py-[16px]">No login history found.</p>}
        {!isLoading && history.map(entry => {
          const locationStr = [entry.city, entry.country].filter(Boolean).join(", ") || "Unknown location";
          const deviceStr   = [entry.browser, entry.os].filter(Boolean).join(" on ") || "Unknown device";
          const dateStr     = new Date(entry.created_at).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
          const isBad       = entry.status === "blocked" || entry.status === "failed";
          return (
            <div key={entry.id} className={`border rounded-[12px] p-[14px] sm:p-[20px] ${isBad ? "border-[#fca5a5] bg-[#fff5f5]" : entry.is_current_session ? "border-[#6366f1] bg-[#f5f3ff]" : "border-[#e5e7eb]"}`}>
              <div className="flex items-start justify-between gap-[12px]">
                <div className="flex items-start gap-[10px] sm:gap-[14px] flex-1 min-w-0">
                  <div className={`w-[36px] h-[36px] sm:w-[40px] sm:h-[40px] rounded-[10px] flex items-center justify-center flex-shrink-0 ${isBad ? "bg-[#fee2e2]" : "bg-[#f0fdf4]"}`}>
                    {isBad ? <AlertTriangle size={16} className="text-[#ef4444]" /> : deviceIcon(entry.device_type)}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-[6px] flex-wrap">
                      <p className="text-[13px] sm:text-[14px] font-semibold text-[#111827]">
                        {entry.is_current_session ? "Current Session" : isBad ? "Failed Login" : "Successful Login"}
                      </p>
                      {entry.is_current_session && <span className="text-[10px] sm:text-[11px] font-medium px-[8px] py-[2px] rounded-full bg-[#d1fae5] text-[#065f46]">Active Now</span>}
                    </div>
                    <div className="mt-[6px] sm:mt-[8px] flex flex-col gap-[3px] sm:gap-[4px]">
                      <div className="flex items-center gap-[6px] text-[11px] sm:text-[12px] text-[#6b7280]"><Monitor  size={12} /> {deviceStr}</div>
                      <div className="flex items-center gap-[6px] text-[11px] sm:text-[12px] text-[#6b7280]"><MapPin   size={12} /> {locationStr}</div>
                      <div className="flex items-center gap-[6px] text-[11px] sm:text-[12px] text-[#6b7280]"><Calendar size={12} /> {dateStr}</div>
                      {entry.ip_address && <div className="flex items-center gap-[6px] text-[11px] sm:text-[12px] text-[#6b7280]"><Wifi size={12} /> IP: {entry.ip_address}</div>}
                    </div>
                  </div>
                </div>
                {!entry.is_current_session && !isBad && <button className="text-[#6b7280] hover:text-[#374151] transition flex-shrink-0"><EyeOff size={16} /></button>}
              </div>
            </div>
          );
        })}
      </div>
      <div className={`${cardPadX} mb-[20px] sm:mb-[28px] bg-[#fffbeb] border border-[#fde68a] rounded-[10px] px-[16px] sm:px-[20px] py-[14px] sm:py-[16px] flex flex-col sm:flex-row sm:items-center justify-between gap-[12px]`}>
        <div className="flex items-start gap-[10px]">
          <AlertTriangle size={18} className="text-[#f59e0b] flex-shrink-0 mt-[1px]" />
          <div>
            <p className="text-[13px] font-semibold text-[#92400e]">Security Tip</p>
            <p className="text-[12px] text-[#92400e] mt-[2px]">Regularly review your login history and revoke access from unrecognized devices.</p>
          </div>
        </div>
        <button onClick={handleSignOutAll} disabled={signingOut}
          className="w-full sm:w-auto flex-shrink-0 h-[36px] px-[14px] border border-[#fde68a] text-[#92400e] text-[12px] font-medium rounded-[8px] hover:bg-[#fef3c7] transition whitespace-nowrap disabled:opacity-60">
          {signingOut ? "Signing out…" : "Sign Out All Devices"}
        </button>
      </div>
    </SectionCard>
  );
};

// ─── Section: Privacy Settings ────────────────────────────────────────────────
const ToggleRow = ({ title, description, checked, onChange }: { title: string; description: string; checked: boolean; onChange: () => void }) => (
  <div className="flex items-center justify-between py-[14px] sm:py-[18px] border-b border-[#f3f4f6] last:border-0 gap-[12px]">
    <div className="min-w-0">
      <p className="text-[13px] sm:text-[14px] font-medium text-[#111827]">{title}</p>
      <p className="text-[11px] sm:text-[12px] text-[#6b7280] mt-[2px]">{description}</p>
    </div>
    <Toggle checked={checked} onChange={onChange} />
  </div>
);

const PrivacySection = () => {
  const [toggles, setToggles] = useState({
    email: true, phone: false, employment: true, visa: false,
    analytics: true, updates: true, marketing: false,
    autoShareEmployer: true, autoShareLawyer: true, requireApproval: false,
  });
  const toggle = (key: keyof typeof toggles) => setToggles(p => ({ ...p, [key]: !p[key] }));
  return (
    <div className="flex flex-col gap-[16px] sm:gap-[20px]">
      <SectionCard>
        <div className={`${cardPad} border-b border-[#f3f4f6]`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-[8px]">
            <div>
              <h3 className="text-[15px] sm:text-[17px] font-semibold text-[#111827]">Profile Visibility</h3>
              <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[2px]">Choose who can view your profile information.</p>
            </div>
            <select className="h-[36px] px-[12px] border border-[#e5e7eb] rounded-[8px] text-[13px] text-[#374151] bg-white focus:outline-none focus:ring-2 focus:ring-[#6366f1] w-full sm:w-auto">
              <option>Team Members Only</option><option>All Users</option><option>Private</option>
            </select>
          </div>
        </div>
        <div className={`${cardPadX} py-[8px] grid grid-cols-1 sm:grid-cols-2 gap-[4px]`}>
          {[
            { key: "email" as const, label: "Email Address", icon: <Mail size={14} /> },
            { key: "phone" as const, label: "Phone Number", icon: <Phone size={14} /> },
            { key: "employment" as const, label: "Employment Info", icon: <Building size={14} /> },
            { key: "visa" as const, label: "Visa Status", icon: <FileText size={14} /> },
          ].map(({ key, label, icon }) => (
            <div key={key} className="flex items-center justify-between py-[12px] sm:py-[14px] px-[12px] sm:px-[16px] rounded-[8px] hover:bg-[#f9fafb]">
              <div className="flex items-center gap-[8px] text-[12px] sm:text-[13px] text-[#374151]">
                <span className="text-[#6b7280]">{icon}</span> {label}
              </div>
              <Toggle checked={toggles[key]} onChange={() => toggle(key)} />
            </div>
          ))}
        </div>
      </SectionCard>
      <SectionCard>
        <div className={`${cardPad} border-b border-[#f3f4f6]`}>
          <h3 className="text-[15px] sm:text-[17px] font-semibold text-[#111827]">Data Sharing & Analytics</h3>
          <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[2px]">Help us improve VisaFlow by sharing anonymous usage data.</p>
        </div>
        <div className={cardPadX}>
          <ToggleRow title="Usage Analytics"          description="Share anonymous data to help us improve features."         checked={toggles.analytics} onChange={() => toggle("analytics")} />
          <ToggleRow title="Product Updates & Tips"   description="Receive personalized tips based on your usage patterns."   checked={toggles.updates}   onChange={() => toggle("updates")}   />
          <ToggleRow title="Marketing Communications" description="Receive promotional emails about new features and offers."  checked={toggles.marketing} onChange={() => toggle("marketing")} />
        </div>
      </SectionCard>
      <SectionCard>
        <div className={`${cardPad} border-b border-[#f3f4f6]`}>
          <h3 className="text-[15px] sm:text-[17px] font-semibold text-[#111827]">Document Access Control</h3>
          <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[2px]">Manage default sharing settings for your immigration documents.</p>
        </div>
        <div className={cardPadX}>
          <ToggleRow title="Auto-share with Employer" description="Automatically grant your employer access to case documents."  checked={toggles.autoShareEmployer} onChange={() => toggle("autoShareEmployer")} />
          <ToggleRow title="Auto-share with Lawyer"   description="Grant your immigration lawyer access to all case documents." checked={toggles.autoShareLawyer}   onChange={() => toggle("autoShareLawyer")}   />
          <ToggleRow title="Require Approval for Sharing" description="Get notified when someone wants to share your documents."  checked={toggles.requireApproval}   onChange={() => toggle("requireApproval")}   />
        </div>
      </SectionCard>
      <SectionCard>
        <div className={`${cardPad} border-b border-[#f3f4f6]`}>
          <h3 className="text-[15px] sm:text-[17px] font-semibold text-[#111827]">Data Retention & Deletion</h3>
          <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[2px]">Manage how long your data is stored and request permanent deletion.</p>
        </div>
        <div className={`${cardPad} flex flex-col gap-[14px] sm:gap-[16px]`}>
          <div className="bg-[#eff6ff] border border-[#bfdbfe] rounded-[10px] p-[14px] sm:p-[20px] flex items-start gap-[12px]">
            <Info size={16} className="text-[#3b82f6] flex-shrink-0 mt-[2px]" />
            <div>
              <p className="text-[13px] font-semibold text-[#1e40af]">Data Retention Policy</p>
              <p className="text-[12px] text-[#1e40af] mt-[4px]">Your case data is retained for 7 years after case completion to comply with immigration record-keeping requirements.</p>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-[10px] p-[14px] sm:p-[16px] border border-[#e5e7eb] rounded-[10px]">
            <div>
              <p className="text-[13px] font-semibold text-[#111827]">Download Your Data</p>
              <p className="text-[12px] text-[#6b7280] mt-[2px]">Export all your personal information and documents.</p>
            </div>
            <button className="flex items-center justify-center gap-[6px] h-[36px] px-[14px] border border-[#e5e7eb] text-[#374151] text-[13px] font-medium rounded-[8px] hover:bg-[#f9fafb] transition w-full sm:w-auto">
              <Download size={13} /> Request Export
            </button>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-[10px] p-[14px] sm:p-[16px] border border-[#fca5a5] rounded-[10px] bg-[#fff5f5]">
            <div>
              <p className="text-[13px] font-semibold text-[#991b1b]">Delete My Account</p>
              <p className="text-[12px] text-[#ef4444] mt-[2px]">Permanently delete your account. This action cannot be undone.</p>
            </div>
            <button className="flex items-center justify-center gap-[6px] h-[36px] px-[14px] bg-[#ef4444] text-white text-[13px] font-medium rounded-[8px] hover:bg-[#dc2626] transition w-full sm:w-auto">
              <Trash2 size={13} /> Delete Account
            </button>
          </div>
        </div>
      </SectionCard>
    </div>
  );
};

// ─── Section: Connected Devices ───────────────────────────────────────────────
const DeviceCard = ({ icon, name, isCurrent, browser, os, lastActive, location }: {
  icon: React.ReactNode; name: string; isCurrent?: boolean;
  browser: string; os: string; lastActive: string; location: string;
}) => (
  <div className={`border rounded-[12px] p-[14px] sm:p-[20px] ${isCurrent ? "border-[#6366f1] bg-[#f5f3ff]" : "border-[#e5e7eb]"}`}>
    <div className="flex items-start justify-between gap-[12px]">
      <div className="flex items-start gap-[10px] sm:gap-[14px] flex-1 min-w-0">
        <div className={`w-[40px] h-[40px] sm:w-[48px] sm:h-[48px] rounded-[12px] flex items-center justify-center flex-shrink-0 ${isCurrent ? "bg-[#e0e7ff]" : "bg-[#f3f4f6]"}`}>{icon}</div>
        <div className="min-w-0">
          <div className="flex items-center gap-[8px] flex-wrap">
            <p className="text-[13px] sm:text-[14px] font-semibold text-[#111827] truncate">{name}</p>
            {isCurrent && <span className="text-[10px] sm:text-[11px] font-medium text-[#6366f1] bg-[#e0e7ff] px-[8px] py-[2px] rounded-full whitespace-nowrap">Current Device</span>}
          </div>
          <div className="mt-[6px] sm:mt-[8px] flex flex-col gap-[3px] sm:gap-[4px]">
            <div className="flex items-center gap-[6px] text-[11px] sm:text-[12px] text-[#6b7280]"><Globe2  size={12} /> {browser}</div>
            <div className="flex items-center gap-[6px] text-[11px] sm:text-[12px] text-[#6b7280]"><Monitor size={12} /> {os}</div>
            <div className="flex items-center gap-[6px] text-[11px] sm:text-[12px] text-[#6b7280]"><Clock   size={12} /> {lastActive}</div>
            <div className="flex items-center gap-[6px] text-[11px] sm:text-[12px] text-[#6b7280]"><MapPin  size={12} /> {location}</div>
          </div>
        </div>
      </div>
      {!isCurrent && (
        <button className="flex-shrink-0 h-[34px] sm:h-[36px] px-[12px] sm:px-[14px] border border-[#e5e7eb] text-[#374151] text-[12px] sm:text-[13px] font-medium rounded-[8px] hover:bg-[#f9fafb] transition whitespace-nowrap">
          Revoke
        </button>
      )}
    </div>
  </div>
);

const ConnectedDevicesSection = () => (
  <SectionCard>
    <div className={`${cardPad} border-b border-[#f3f4f6] flex flex-col sm:flex-row sm:items-start justify-between gap-[8px]`}>
      <div>
        <h2 className="text-[17px] sm:text-[20px] font-semibold text-[#111827]">Connected Devices</h2>
        <p className="text-[13px] sm:text-[14px] text-[#6b7280] mt-[4px]">Manage devices that have access to your VisaFlow account.</p>
      </div>
      <span className="text-[12px] sm:text-[13px] font-medium text-[#6366f1] bg-[#e0e7ff] px-[12px] py-[6px] rounded-full whitespace-nowrap w-fit">4 Active Devices</span>
    </div>
    <div className={`${cardPad} flex flex-col gap-[10px] sm:gap-[12px]`}>
      <DeviceCard icon={<Laptop     size={22} className="text-[#6366f1]" />} name='MacBook Pro 16"'     isCurrent browser="Chrome 120" os="macOS Sonoma"    lastActive="Just now"    location="San Francisco, CA" />
      <DeviceCard icon={<Smartphone size={22} className="text-[#374151]" />} name="iPhone 14 Pro"                 browser="Safari Mobile"    os="iOS 17.2"           lastActive="2 hours ago" location="San Francisco, CA" />
      <DeviceCard icon={<Tablet     size={22} className="text-[#374151]" />} name="iPad Air"                      browser="Chrome Mobile"    os="iPadOS 17.2"        lastActive="1 day ago"   location="San Francisco, CA" />
      <DeviceCard icon={<Laptop     size={22} className="text-[#374151]" />} name='Work Laptop'                   browser="Chrome 119"       os="macOS Ventura"      lastActive="3 days ago"  location="San Francisco, CA" />
    </div>
    <div className={`${cardPadX} mb-[20px] sm:mb-[28px] bg-[#fef3c7] border border-[#fde68a] rounded-[10px] px-[16px] sm:px-[20px] py-[14px] sm:py-[16px] flex flex-col sm:flex-row sm:items-center justify-between gap-[12px]`}>
      <div className="flex items-start gap-[10px]">
        <AlertTriangle size={18} className="text-[#f59e0b] flex-shrink-0 mt-[1px]" />
        <div>
          <p className="text-[13px] font-semibold text-[#92400e]">Suspicious Activity?</p>
          <p className="text-[12px] text-[#92400e] mt-[2px]">If you see a device you don't recognize, revoke its access and change your password.</p>
        </div>
      </div>
      <button className="w-full sm:w-auto flex-shrink-0 h-[36px] px-[14px] bg-[#f59e0b] text-white text-[12px] font-medium rounded-[8px] hover:bg-[#d97706] transition whitespace-nowrap">Sign Out All</button>
    </div>
  </SectionCard>
);

// ─── Section: Session Settings ────────────────────────────────────────────────
const SessionSection = () => {
  const [rememberMe, setRememberMe] = useState(true);
  const [concurrent, setConcurrent] = useState(true);
  return (
    <SectionCard>
      <div className={`${cardPad} border-b border-[#f3f4f6]`}>
        <h2 className="text-[17px] sm:text-[20px] font-semibold text-[#111827]">Session Settings</h2>
        <p className="text-[13px] sm:text-[14px] text-[#6b7280] mt-[4px]">Configure how long you stay signed in and when your session expires.</p>
      </div>
      <div className={`${cardPad} flex flex-col gap-[16px] sm:gap-[24px]`}>
        {[
          {
            title: "Automatic Sign Out", desc: "Choose when to automatically sign out after inactivity.",
            extra: (
              <select className="h-[36px] px-[12px] border border-[#e5e7eb] rounded-[8px] text-[13px] text-[#374151] bg-[#f9fafb] focus:outline-none focus:ring-2 focus:ring-[#6366f1] w-full sm:w-auto">
                <option>15 minutes</option><option>30 minutes</option><option>1 hour</option><option>4 hours</option>
              </select>
            ),
          },
        ].map(({ title, desc, extra }) => (
          <div key={title} className="border border-[#e5e7eb] rounded-[12px] p-[16px] sm:p-[24px]">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-[10px]">
              <div><h3 className="text-[14px] sm:text-[15px] font-semibold text-[#111827]">{title}</h3><p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[2px]">{desc}</p></div>
              {extra}
            </div>
            <div className="mt-[12px] sm:mt-[16px] flex items-start gap-[8px] bg-[#eff6ff] rounded-[8px] px-[12px] sm:px-[14px] py-[10px] sm:py-[12px]">
              <Info size={14} className="text-[#3b82f6] flex-shrink-0 mt-[1px]" />
              <p className="text-[11px] sm:text-[12px] text-[#1e40af]">We recommend setting a timeout of 1 hour or less when accessing VisaFlow from shared computers.</p>
            </div>
          </div>
        ))}
        <div className="border border-[#e5e7eb] rounded-[12px] p-[16px] sm:p-[24px]">
          <div className="flex items-start justify-between gap-[12px]">
            <div className="flex-1 min-w-0">
              <h3 className="text-[14px] sm:text-[15px] font-semibold text-[#111827]">Remember Me</h3>
              <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[4px]">Stay signed in on this device for 30 days without requiring login credentials.</p>
            </div>
            <Toggle checked={rememberMe} onChange={() => setRememberMe(!rememberMe)} />
          </div>
        </div>
        <div className="border border-[#e5e7eb] rounded-[12px] p-[16px] sm:p-[24px]">
          <div className="flex items-start justify-between gap-[12px]">
            <div className="flex-1 min-w-0">
              <h3 className="text-[14px] sm:text-[15px] font-semibold text-[#111827]">Concurrent Sessions</h3>
              <p className="text-[12px] sm:text-[13px] text-[#6b7280] mt-[4px]">Allow multiple active sessions on different devices simultaneously.</p>
              <div className="mt-[12px] border border-[#e5e7eb] rounded-[8px] overflow-hidden">
                <div className="flex items-center justify-between px-[14px] sm:px-[16px] py-[10px] sm:py-[12px] border-b border-[#f3f4f6]">
                  <span className="text-[12px] sm:text-[13px] text-[#6b7280]">Maximum concurrent sessions:</span>
                  <span className="text-[16px] sm:text-[18px] font-bold text-[#111827]">5</span>
                </div>
                <div className="flex items-center justify-between px-[14px] sm:px-[16px] py-[10px] sm:py-[12px]">
                  <span className="text-[12px] sm:text-[13px] text-[#6b7280]">Currently active:</span>
                  <span className="text-[16px] sm:text-[18px] font-bold text-[#6366f1]">4</span>
                </div>
              </div>
            </div>
            <Toggle checked={concurrent} onChange={() => setConcurrent(!concurrent)} />
          </div>
        </div>
      </div>
    </SectionCard>
  );
};

// ─── Section: Security Alerts ─────────────────────────────────────────────────
const AlertRow = ({ title, description, emailChecked, smsChecked, onEmailChange, onSmsChange }: {
  title: string; description: string; emailChecked: boolean; smsChecked: boolean;
  onEmailChange: () => void; onSmsChange: () => void;
}) => (
  <div className="flex items-start sm:items-center justify-between py-[14px] sm:py-[18px] border-b border-[#f3f4f6] last:border-0 gap-[12px]">
    <div className="flex-1 min-w-0">
      <p className="text-[13px] sm:text-[14px] font-medium text-[#111827]">{title}</p>
      <p className="text-[11px] sm:text-[12px] text-[#6b7280] mt-[2px]">{description}</p>
    </div>
    <div className="flex items-center gap-[12px] sm:gap-[16px] flex-shrink-0">
      <label className="flex items-center gap-[5px] sm:gap-[6px] cursor-pointer">
        <Checkbox checked={emailChecked} onChange={onEmailChange} />
        <span className="text-[11px] sm:text-[12px] text-[#6b7280]">Email</span>
      </label>
      <label className="flex items-center gap-[5px] sm:gap-[6px] cursor-pointer">
        <Checkbox checked={smsChecked} onChange={onSmsChange} />
        <span className="text-[11px] sm:text-[12px] text-[#6b7280]">SMS</span>
      </label>
    </div>
  </div>
);

const SecurityAlertsSection = () => {
  const [alerts, setAlerts] = useState({
    newDevice:        { email: true,  sms: true  },
    failedLogin:      { email: true,  sms: true  },
    passwordChanged:  { email: true,  sms: false },
    settingsModified: { email: true,  sms: false },
    unusualActivity:  { email: true,  sms: true  },
  });
  type AlertKey = keyof typeof alerts;
  const toggle = (key: AlertKey, ch: "email" | "sms") => setAlerts(p => ({ ...p, [key]: { ...p[key], [ch]: !p[key][ch] } }));

  return (
    <SectionCard>
      <div className={`${cardPad} border-b border-[#f3f4f6]`}>
        <h2 className="text-[17px] sm:text-[20px] font-semibold text-[#111827]">Security Alerts & Notifications</h2>
        <p className="text-[13px] sm:text-[14px] text-[#6b7280] mt-[4px]">Get notified about important security events related to your account.</p>
      </div>
      <div className={cardPadX}>
        <AlertRow title="New Device Login"           description="Alerted when your account is accessed from a new device."         emailChecked={alerts.newDevice.email}        smsChecked={alerts.newDevice.sms}        onEmailChange={() => toggle("newDevice","email")}        onSmsChange={() => toggle("newDevice","sms")} />
        <AlertRow title="Failed Login Attempts"      description="Notifications when someone fails to log in multiple times."       emailChecked={alerts.failedLogin.email}      smsChecked={alerts.failedLogin.sms}      onEmailChange={() => toggle("failedLogin","email")}      onSmsChange={() => toggle("failedLogin","sms")} />
        <AlertRow title="Password Changed"           description="Get notified immediately when your password is changed."          emailChecked={alerts.passwordChanged.email}  smsChecked={alerts.passwordChanged.sms}  onEmailChange={() => toggle("passwordChanged","email")}  onSmsChange={() => toggle("passwordChanged","sms")} />
        <AlertRow title="Security Settings Modified" description="Alerted when 2FA or privacy settings are changed."               emailChecked={alerts.settingsModified.email} smsChecked={alerts.settingsModified.sms} onEmailChange={() => toggle("settingsModified","email")} onSmsChange={() => toggle("settingsModified","sms")} />
        <AlertRow title="Unusual Activity Detected"  description="Alerts when our system detects suspicious behavior."             emailChecked={alerts.unusualActivity.email}  smsChecked={alerts.unusualActivity.sms}  onEmailChange={() => toggle("unusualActivity","email")}  onSmsChange={() => toggle("unusualActivity","sms")} />
      </div>
      <div className={`${cardPadX} mb-[20px] sm:mb-[28px] mt-[8px] bg-[#f0fdf4] border border-[#bbf7d0] rounded-[10px] px-[16px] sm:px-[20px] py-[14px] sm:py-[16px]`}>
        <div className="flex items-start gap-[10px]">
          <CheckCircle size={18} className="text-[#10b981] flex-shrink-0 mt-[1px]" />
          <div>
            <p className="text-[13px] font-semibold text-[#065f46]">Your Account is Secure</p>
            <p className="text-[12px] text-[#065f46] mt-[2px]">All recommended security features are enabled. Keep these settings active to protect your sensitive immigration data.</p>
          </div>
        </div>
      </div>
    </SectionCard>
  );
};

// ─── Section titles ───────────────────────────────────────────────────────────
const SECTION_TITLES: Record<SectionId, { title: string; subtitle: string }> = {
  profile:           { title: "Profile & Security",              subtitle: "Manage your account settings and security preferences" },
  authentication:    { title: "Authentication Methods",          subtitle: "Configure how you log in and connect external accounts." },
  mfa:               { title: "Multi-Factor Authentication",     subtitle: "Add an extra layer of security to your account." },
  "login-history":   { title: "Login History",                   subtitle: "Review recent access to your account." },
  privacy:           { title: "Privacy Settings",                subtitle: "Control who can see your information and how your data is used." },
  devices:           { title: "Connected Devices",               subtitle: "Manage all devices that have access to your account." },
  session:           { title: "Session Settings",                subtitle: "Configure how long you stay signed in." },
  "security-alerts": { title: "Security Alerts",                 subtitle: "Get notified about important security events." },
};

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ProfileSecurity() {
  const location = useLocation();

  const getSection = (): SectionId => {
    const path = location.pathname;
    if (path === "/profile/authentication")  return "authentication";
    if (path === "/profile/mfa")             return "mfa";
    if (path === "/profile/login-history")   return "login-history";
    if (path === "/profile/privacy")         return "privacy";
    if (path === "/profile/devices")         return "devices";
    if (path === "/profile/session")         return "session";
    if (path === "/profile/security-alerts") return "security-alerts";
    return "profile";
  };

  const activeSection = getSection();
  const { title, subtitle } = SECTION_TITLES[activeSection];

  const SECTION_COMPONENTS: Record<SectionId, React.ReactNode> = {
    profile:           <PersonalInfoSection />,
    authentication:    <AuthenticationSection />,
    mfa:               <MFASection />,
    "login-history":   <LoginHistorySection />,
    privacy:           <PrivacySection />,
    devices:           <ConnectedDevicesSection />,
    session:           <SessionSection />,
    "security-alerts": <SecurityAlertsSection />,
  };

  return (
    <div className="flex flex-col h-full bg-[#f9fafb]" style={{ fontFamily: "Inter, sans-serif" }}>
      <PageHeader title={title} subtitle={subtitle} showBell={false} />
      <PageContent>
        <div className="max-w-[900px]">
          {SECTION_COMPONENTS[activeSection]}
        </div>
      </PageContent>
    </div>
  );
}