import { useMemo, useState } from "react";
import {
  useBookConsultation,
  useCreateConsultationBooking,
} from "../../hooks/employee/useBookConsultation";
import {
  formatUsd,
  parseJsonText,
} from "../../types/employee/bookConsultation.types";
import type {
  AppointmentType,
  ConsultationFormat,
  ConsultationSlot,
} from "../../types/employee/bookConsultation.types";

import starIcon          from "../../assets/icons/star.svg";
import languageIcon      from "../../assets/icons/language.svg";
import locationIcon      from "../../assets/icons/location.svg";
import briefcaseIcon     from "../../assets/icons/briefcase.svg";
import checkCircleIcon   from "../../assets/icons/check-circle.svg";
import chevronLeftIcon   from "../../assets/icons/chevron-left.svg";
import chevronRightIcon  from "../../assets/icons/chevron-right.svg";
import radioSelectedIcon   from "../../assets/icons/radio-selected.svg";
import radioUnselectedIcon from "../../assets/icons/radio-unselected.svg";
import arrowRightIcon    from "../../assets/icons/arrow-right.svg";

const fallbackAppointmentTypes: AppointmentType[] = [
  { id: "intro",        title: "15-Min Intro Call",     description: "Quick case overview",      duration_minutes: 15, price_usd: 75  },
  { id: "consultation", title: "30-Min Consultation",   description: "Detailed discussion",      duration_minutes: 30, price_usd: 150 },
  { id: "case_review",  title: "60-Min Case Review",    description: "Comprehensive analysis",   duration_minutes: 60, price_usd: 275 },
];

const fallbackSlots: ConsultationSlot[] = [
  { id: "slot-1", date: "2025-01-14", time: "9:00 AM",  timezone: "PST", availability: "high"    },
  { id: "slot-2", date: "2025-01-14", time: "10:00 AM", timezone: "PST", availability: "high"    },
  { id: "slot-3", date: "2025-01-14", time: "11:30 AM", timezone: "PST", availability: "high"    },
  { id: "slot-4", date: "2025-01-14", time: "1:00 PM",  timezone: "PST", availability: "high"    },
  { id: "slot-5", date: "2025-01-14", time: "2:30 PM",  timezone: "PST", availability: "limited" },
  { id: "slot-6", date: "2025-01-14", time: "3:30 PM",  timezone: "PST", availability: "limited" },
];

const availableDays = [15, 16, 17, 20, 21, 22, 27, 28, 29];
const limitedDays   = [18, 23];

export default function BookConsultation() {
  const { data, loading } = useBookConsultation();

  const appointmentTypes = data?.appointment_types?.length ? data.appointment_types : fallbackAppointmentTypes;
  const slots    = data?.slots?.length ? data.slots : fallbackSlots;
  const attorney = data?.attorney;

  const [selectedTypeId, setSelectedTypeId] = useState(fallbackAppointmentTypes[0].id);
  const [selectedSlotId, setSelectedSlotId] = useState(fallbackSlots[2].id);
  const [format, setFormat] = useState<ConsultationFormat>("virtual");

  const selectedType = appointmentTypes.find(i => i.id === selectedTypeId) ?? appointmentTypes[0];
  const selectedSlot = slots.find(i => i.id === selectedSlotId) ?? slots[0];
  const booking      = useCreateConsultationBooking();

  const attorneyName = useMemo(() => {
    if (attorney?.user) return `${attorney.user.first_name} ${attorney.user.last_name}, Esq.`;
    return "Sarah Martinez, Esq.";
  }, [attorney]);

  const languages = parseJsonText(attorney?.languages ?? null);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-[64px]">
        <p className="text-[14px] text-[#4b5563]">Loading consultation...</p>
      </div>
    );
  }

  return (
    // ── Single outer wrapper — padding lives here only ──────────────────────
    <div className="flex flex-col gap-[32px] px-[24px] sm:px-[32px] pt-[12px] pb-[140px]">

      {/* ── Step bar ── */}
      <div className="border-b border-[#e5e7eb] bg-white py-[16px] -mx-[24px] sm:-mx-[32px] px-[24px] sm:px-[32px]">
        <div className="flex items-center justify-center gap-[16px]">
          <div className="flex items-center gap-[12px]">
            <img src={checkCircleIcon} alt="" className="size-[32px]" />
            <p className="text-[14px] font-semibold text-[#111827]">Select Attorney</p>
          </div>
          <div className="h-[4px] w-[64px] bg-[#2563eb]" />
          <div className="flex items-center gap-[12px]">
            <div className="flex size-[32px] items-center justify-center rounded-full bg-gradient-to-r from-[#2563eb] to-[#9333ea] text-[14px] font-bold text-white">
              2
            </div>
            <p className="text-[14px] font-semibold text-[#111827]">Book Consultation</p>
          </div>
        </div>
      </div>

      {/* ── Page heading ── */}
      <div>
        <h1 className="text-[30px] font-bold leading-[36px] text-[#111827]">Book Your Consultation</h1>
        <p className="mt-[8px] text-[16px] leading-[24px] text-[#4b5563]">
          Select your preferred date, time, and consultation type
        </p>
      </div>

      {/* ── Main grid ── */}
      <div className="grid grid-cols-1 gap-[32px] xl:grid-cols-[300px_1fr]">

        {/* ── Sidebar: attorney card ── */}
        <aside className="rounded-[16px] border border-[#e5e7eb] bg-white p-[25px] shadow-sm">
          <div className="mb-[16px] flex items-center justify-between">
            <h2 className="text-[18px] font-bold leading-[28px] text-[#111827]">Selected Attorney</h2>
            <button className="text-[14px] font-medium text-[#2563eb]">Change</button>
          </div>

          <img
            alt={attorneyName}
            className="h-[192px] w-full rounded-[12px] border-2 border-[#e5e7eb] object-cover"
          />

          <h3 className="mt-[16px] text-[20px] font-bold leading-[28px] text-[#111827]">{attorneyName}</h3>
          <p className="mt-[8px] text-[16px] leading-[24px] text-[#4b5563]">
            {attorney?.law_firm_name ?? "Martinez Immigration Law Group"}
          </p>

          <div className="mt-[8px] flex items-center gap-[8px]">
            <img src={starIcon} alt="" className="size-[16px]" />
            <span className="text-[16px] font-bold text-[#111827]">4.9</span>
            <span className="text-[14px] text-[#4b5563]">(287 reviews)</span>
          </div>

          <div className="mt-[16px] space-y-[8px] border-b border-[#e5e7eb] pb-[17px]">
            <p className="flex items-center gap-[8px] text-[14px] leading-[20px] text-[#374151]">
              <img src={languageIcon} alt="" className="size-[16px]" />
              {languages.length ? languages.join(", ") : "English, Spanish"}
            </p>
            <p className="flex items-center gap-[8px] text-[14px] leading-[20px] text-[#374151]">
              <img src={locationIcon} alt="" className="size-[16px]" />
              {attorney?.bar_state ?? "Beverly Hills, CA"} (2.3 mi)
            </p>
            <p className="flex items-center gap-[8px] text-[14px] leading-[20px] text-[#374151]">
              <img src={briefcaseIcon} alt="" className="size-[16px]" />
              {attorney?.years_experience ?? 15}+ Years Experience
            </p>
          </div>

          <div className="mt-[24px] rounded-[8px] border border-[#bfdbfe] bg-[#eff6ff] p-[17px]">
            <p className="text-[12px] font-semibold leading-[16px] text-[#1d4ed8]">STARTING PRICE</p>
            <p className="mt-[4px] bg-gradient-to-r from-[#2563eb] to-[#9333ea] bg-clip-text text-[24px] font-bold leading-[32px] text-transparent">
              $150
            </p>
            <p className="text-[12px] leading-[16px] text-[#4b5563]">per consultation</p>
          </div>

          <div className="mt-[24px] space-y-[8px]">
            <p className="text-[12px] font-semibold leading-[16px] text-[#374151]">POLICIES</p>
            {["Free cancellation up to 24h before", "Reschedule anytime before 12h", "Secure payment processing"].map(item => (
              <p key={item} className="text-[12px] leading-[16px] text-[#4b5563]">
                <span className="text-[#22c55e]">✓</span> {item}
              </p>
            ))}
          </div>
        </aside>

        {/* ── Main content ── */}
        <main className="flex flex-col gap-[24px]">

          {/* Appointment type */}
          <section className="rounded-[16px] border border-[#e5e7eb] bg-white p-[25px] shadow-sm">
            <h3 className="mb-[16px] text-[18px] font-bold leading-[28px] text-[#111827]">
              Select Appointment Type
            </h3>
            <div className="grid grid-cols-1 gap-[16px] sm:grid-cols-2 xl:grid-cols-3">
              {appointmentTypes.map(item => {
                const active = selectedTypeId === item.id;
                return (
                  <button key={item.id} onClick={() => setSelectedTypeId(item.id)}
                    className={`h-[168px] rounded-[12px] border-2 p-[16px] text-left transition-colors ${
                      active ? "border-[#3b82f6] bg-[#eff6ff]" : "border-[#e5e7eb] bg-white hover:border-[#93c5fd]"
                    }`}>
                    <div className={`mb-[16px] flex size-[40px] items-center justify-center rounded-[8px] ${
                      active ? "bg-gradient-to-br from-[#2563eb] to-[#9333ea]" : "bg-[#e5e7eb]"
                    }`}>
                      <span className={active ? "text-white" : "text-[#4b5563]"}>☎</span>
                    </div>
                    <p className="text-[16px] font-bold leading-[24px] text-[#111827]">{item.title}</p>
                    <p className="mt-[2px] text-[14px] leading-[20px] text-[#4b5563]">{item.description}</p>
                    <p className={`mt-[12px] text-[20px] font-bold leading-[28px] ${
                      active ? "bg-gradient-to-r from-[#2563eb] to-[#9333ea] bg-clip-text text-transparent" : "text-[#111827]"
                    }`}>
                      {formatUsd(item.price_usd)}
                    </p>
                  </button>
                );
              })}
            </div>

            <div className="mt-[24px] flex flex-wrap items-center gap-[12px]">
              <p className="text-[14px] font-semibold leading-[20px] text-[#374151]">Consultation Format:</p>
              {(["virtual", "in_person"] as ConsultationFormat[]).map(f => (
                <button key={f} onClick={() => setFormat(f)}
                  className={`rounded-[8px] px-[16px] py-[9px] text-[14px] font-medium transition-all ${
                    format === f
                      ? "bg-gradient-to-r from-[#2563eb] to-[#9333ea] text-white shadow"
                      : "border border-[#d1d5db] text-[#374151] hover:border-[#93c5fd]"
                  }`}>
                  {f === "virtual" ? "Virtual" : "In-Person"}
                </button>
              ))}
            </div>
          </section>

          {/* Date & time */}
          <section className="rounded-[16px] border border-[#e5e7eb] bg-white p-[25px] shadow-sm">
            <div className="mb-[24px] flex flex-wrap items-center justify-between gap-[16px]">
              <h3 className="text-[18px] font-bold leading-[28px] text-[#111827]">Select Date & Time</h3>
              <div className="flex items-center gap-[12px]">
                <span className="text-[14px] font-medium text-[#374151]">Timezone:</span>
                <select className="rounded-[8px] border border-[#d1d5db] px-[17px] py-[9px] text-[14px]">
                  <option>PST (UTC-8)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-[24px] xl:grid-cols-2">
              {/* Calendar */}
              <div>
                <div className="mb-[16px] flex items-center justify-between">
                  <button className="flex size-[40px] items-center justify-center rounded-[8px] border border-[#d1d5db] hover:bg-[#f9fafb]">
                    <img src={chevronLeftIcon} alt="" className="size-[16px]" />
                  </button>
                  <h4 className="text-[18px] font-bold leading-[28px] text-[#111827]">January 2025</h4>
                  <button className="flex size-[40px] items-center justify-center rounded-[8px] border border-[#d1d5db] hover:bg-[#f9fafb]">
                    <img src={chevronRightIcon} alt="" className="size-[16px]" />
                  </button>
                </div>

                <div className="grid grid-cols-7 gap-[4px]">
                  {["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].map(day => (
                    <div key={day} className="py-[8px] text-center text-[12px] font-semibold leading-[16px] text-[#4b5563]">
                      {day}
                    </div>
                  ))}
                  <div className="col-span-3" />
                  {Array.from({ length: 31 }, (_, i) => i + 1).map(day => {
                    const active  = day === 14;
                    const high    = availableDays.includes(day);
                    const limited = limitedDays.includes(day);
                    return (
                      <button key={day}
                        className={`relative flex h-[40px] w-full items-center justify-center rounded-[8px] text-[14px] font-medium transition-colors ${
                          active ? "bg-gradient-to-r from-[#2563eb] to-[#9333ea] text-white" : "text-[#111827] hover:bg-[#f3f4f6]"
                        }`}>
                        {day}
                        {(high || limited || active) && (
                          <span className={`absolute bottom-[4px] size-[4px] rounded-full ${
                            active ? "bg-white" : limited ? "bg-[#eab308]" : "bg-[#22c55e]"
                          }`} />
                        )}
                      </button>
                    );
                  })}
                </div>

                <div className="mt-[17px] flex flex-wrap gap-[16px] border-t border-[#e5e7eb] pt-[17px]">
                  <p className="text-[12px] leading-[16px] text-[#4b5563]"><span className="text-[#22c55e]">●</span> High availability</p>
                  <p className="text-[12px] leading-[16px] text-[#4b5563]"><span className="text-[#eab308]">●</span> Limited slots</p>
                </div>
              </div>

              {/* Time slots */}
              <div>
                <h4 className="text-[16px] font-bold leading-[24px] text-[#111827]">Tuesday, January 14, 2025</h4>
                <p className="mt-[4px] text-[14px] leading-[20px] text-[#4b5563]">{slots.length} slots available</p>
                <div className="mt-[16px] flex max-h-[384px] flex-col gap-[10px] overflow-y-auto pr-[4px]">
                  {slots.map(slot => {
                    const active = selectedSlotId === slot.id;
                    return (
                      <button key={slot.id} onClick={() => setSelectedSlotId(slot.id)}
                        className={`flex items-center justify-between rounded-[8px] px-[17px] py-[13px] text-left transition-colors ${
                          active ? "border-2 border-[#3b82f6] bg-[#eff6ff]" : "border border-[#d1d5db] bg-white hover:border-[#93c5fd]"
                        }`}>
                        <div>
                          <p className="text-[16px] font-semibold leading-[24px] text-[#111827]">{slot.time}</p>
                          <p className="text-[12px] leading-[16px] text-[#4b5563]">{slot.timezone}</p>
                        </div>
                        <img src={active ? radioSelectedIcon : radioUnselectedIcon} alt="" className="size-[16px]" />
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>

      {/* ── Fixed booking summary bar ── */}
      <div className="fixed bottom-0 left-0 right-0 xl:left-[260px] z-[50] border-t-2 border-[#e5e7eb] bg-white px-[24px] py-[16px] shadow-2xl xl:px-[48px]">
        <div className="flex flex-col gap-[16px] xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-[16px]">
            <div>
              <p className="text-[14px] font-semibold leading-[20px] text-[#111827]">{selectedType.title}</p>
              <p className="text-[12px] leading-[16px] text-[#4b5563]">
                {format === "virtual" ? "Virtual consultation" : "In-person consultation"}
              </p>
            </div>
            <div className="hidden h-[40px] w-px bg-[#d1d5db] sm:block" />
            <div>
              <p className="text-[14px] font-semibold leading-[20px] text-[#111827]">Tue, Jan 14, 2025</p>
              <p className="text-[12px] leading-[16px] text-[#4b5563]">{selectedSlot.time} {selectedSlot.timezone}</p>
            </div>
            <div className="hidden h-[40px] w-px bg-[#d1d5db] sm:block" />
            <div>
              <p className="text-[14px] font-semibold leading-[20px] text-[#111827]">Total Price</p>
              <p className="bg-gradient-to-r from-[#2563eb] to-[#9333ea] bg-clip-text text-[18px] font-bold leading-[28px] text-transparent">
                {formatUsd(selectedType.price_usd)}
              </p>
            </div>
          </div>

          <button
            disabled={booking.loading || !attorney?.id}
            onClick={() => {
              if (!attorney?.id) return;
              booking.submit({
                attorney_id:         attorney.id,
                appointment_type_id: selectedType.id,
                consultation_format: format,
                slot_id:             selectedSlot.id,
              });
            }}
            className="flex items-center justify-center gap-[12px] rounded-[12px] bg-gradient-to-r from-[#2563eb] to-[#9333ea] px-[32px] py-[14px] text-[16px] font-bold text-white shadow-lg hover:opacity-90 disabled:opacity-60 transition-opacity"
          >
            <span>{booking.loading ? "Booking..." : "Confirm Booking"}</span>
            {!booking.loading && <img src={arrowRightIcon} alt="" className="size-[18px]" />}
          </button>
        </div>

        {booking.error && (
          <p className="mt-[8px] text-right text-[14px] text-[#dc2626]">{booking.error}</p>
        )}
      </div>

    </div>
  );
}