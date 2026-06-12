// src/api/lawyer/intake.api.ts
//
// All Client Intake endpoints (lawyer side).
// Base URL is set in src/api/axios.ts (e.g. /api/v1).
// Note: All endpoints in this file use JWT (axios attaches token).
// The /intake/by-token/{token} client-side endpoint is intentionally NOT here —
// it should be called from a public route with a separate, unauthed axios.

import axios from '../axios';

import type {
  IntakeSession,
  IntakeData,
  VisaStatusOptionsResponse,
  CreateSessionPayload,
  GenerateLinkResponse,
  SaveDraftResponse,
  SubmitResponse,
  SaveIntakeDataParams,
  SaveIntakeDataPayload,
} from '../../types/lawyer/intake.types';

/* ── Visa status dropdown options ───────────────────────────────────── */
export async function getVisaStatusOptions(): Promise<VisaStatusOptionsResponse> {
  const res = await axios.get<VisaStatusOptionsResponse>('/intake/visa-status-options');
  return res.data;
}

/* ── Session CRUD ───────────────────────────────────────────────────── */
export async function createIntakeSession(
  payload: CreateSessionPayload,
): Promise<IntakeSession> {
  const res = await axios.post<IntakeSession>('/intake/sessions', payload);
  return res.data;
}

export async function getIntakeSession(sessionId: string): Promise<IntakeSession> {
  const res = await axios.get<IntakeSession>(`/intake/sessions/${sessionId}`);
  return res.data;
}

/* ── Generate / rotate client link (Step 3 button) ──────────────────── */
export async function generateClientLink(
  sessionId: string,
): Promise<GenerateLinkResponse> {
  const res = await axios.post<GenerateLinkResponse>(
    `/intake/sessions/${sessionId}/generate-link`,
  );
  return res.data;
}

/* ── Save Draft (top-right button) ──────────────────────────────────── */
export async function saveDraft(sessionId: string): Promise<SaveDraftResponse> {
  const res = await axios.post<SaveDraftResponse>(
    `/intake/sessions/${sessionId}/save-draft`,
  );
  return res.data;
}

/* ── Final submit (Step 5) ──────────────────────────────────────────── */
export async function submitIntake(sessionId: string): Promise<SubmitResponse> {
  const res = await axios.post<SubmitResponse>(`/intake/sessions/${sessionId}/submit`);
  return res.data;
}

/* ── Load intake data (called on each step mount) ──────────────────── */
export async function getIntakeData(sessionId: string): Promise<IntakeData | null> {
  // 204 No Content means nothing saved yet.
  const res = await axios.get<IntakeData>(`/intake/sessions/${sessionId}/data`, {
    validateStatus: (s) => s === 200 || s === 204,
  });
  if (res.status === 204) return null;
  return res.data;
}

/* ── Save intake data (auto-save, Save Draft, or Continue) ─────────── */
export async function saveIntakeData(
  sessionId: string,
  data: SaveIntakeDataPayload,
  params: SaveIntakeDataParams = {},
): Promise<IntakeData> {
  const res = await axios.put<IntakeData>(
    `/intake/sessions/${sessionId}/data`,
    data,
    { params },
  );
  return res.data;
}

/* ── Aggregated client profile (Screen 26) ──────────────────────────── */
export async function getClientProfile(clientId: string) {
  const res = await axios.get(`/clients/${clientId}/profile`);
  return res.data;
}

/* ── Bundled export — easier to mock in tests ───────────────────────── */
export const intakeApi = {
  getVisaStatusOptions,
  createIntakeSession,
  getIntakeSession,
  generateClientLink,
  saveDraft,
  submitIntake,
  getIntakeData,
  saveIntakeData,
  getClientProfile,
};