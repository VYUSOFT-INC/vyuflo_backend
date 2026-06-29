export type ConsultationFormat = "virtual" | "in_person";

export interface AttorneyProfile {
  id: string;
  user_id: string;
  bar_number: string | null;
  bar_state: string | null;
  years_experience: number | null;
  law_firm_name: string | null;
  specialisations: string | null;
  languages: string | null;
  availability_note: string | null;
  max_active_cases: number | null;
  bio: string | null;
  profile_photo_url: string | null;
  is_accepting_cases: boolean;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  user?: {
    id: string;
    first_name: string;
    last_name: string;
    email: string;
    phone: string | null;
  };
}

export interface AppointmentType {
  id: string;
  title: string;
  description: string;
  duration_minutes: number;
  price_usd: number;
}

export interface ConsultationSlot {
  id: string;
  date: string;
  time: string;
  timezone: string;
  availability: "high" | "limited" | "none";
}

export interface BookConsultationData {
  attorney: AttorneyProfile | null;
  appointment_types: AppointmentType[];
  slots: ConsultationSlot[];
}

export interface CreateConsultationBookingRequest {
  attorney_id: string;
  appointment_type_id: string;
  consultation_format: ConsultationFormat;
  slot_id: string;
}

export interface CreateConsultationBookingResponse {
  id: string;
  status: string;
  message?: string;
}

export function formatUsd(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function parseJsonText(value: string | null): string[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [value];
  } catch {
    return value.split(",").map((x) => x.trim()).filter(Boolean);
  }
}