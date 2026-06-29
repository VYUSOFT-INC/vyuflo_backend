import type {
  AttorneyProfile,
  BookConsultationData,
  CreateConsultationBookingRequest,
  CreateConsultationBookingResponse,
} from "../types/bookConsultation.types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("access_token");

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail ?? `Request failed: ${res.status}`);
  }

  return res.json();
}

export const listAttorneys = (): Promise<AttorneyProfile[]> =>
  request("/api/v1/attorneys");

export const getSelectedAttorney = (attorneyId: string): Promise<AttorneyProfile> =>
  request(`/api/v1/attorneys/${attorneyId}`);

export const getBookConsultationData = (
  attorneyId?: string
): Promise<BookConsultationData> => {
  const query = attorneyId ? `?attorney_id=${attorneyId}` : "";
  return request(`/api/v1/consultations/book-page${query}`);
};

export const createConsultationBooking = (
  body: CreateConsultationBookingRequest
): Promise<CreateConsultationBookingResponse> =>
  request("/api/v1/consultations/bookings", {
    method: "POST",
    body: JSON.stringify(body),
  });