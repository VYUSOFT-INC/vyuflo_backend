// src/api/invitation.api.ts
import axiosInstance from "../axios";
import type {
  InviteByEmailRequest,
  InviteByCodeRequest,
  InviteByLinkRequest,
  AcceptInviteRequest,
  UpdateEmployeeRequest,
  InvitationResponse,
  InvitationListResponse,
  AcceptInviteResponse,
  EmployeeListResponse,
  ValidateTokenResponse,
} from "../../types/hr/invitation.types";

const BASE = "/invitations";

// ── HR: Create Invitations ────────────────────────────────────────────────────

export const invitationApi = {

  // HR invites by email
  inviteByEmail: async (data: InviteByEmailRequest): Promise<InvitationResponse> => {
    const res = await axiosInstance.post(`${BASE}/email`, data);
    return res.data;
  },

  // HR creates company code
  inviteByCode: async (data: InviteByCodeRequest): Promise<InvitationResponse> => {
    const res = await axiosInstance.post(`${BASE}/code`, data);
    return res.data;
  },

  // HR creates shareable link
  inviteByLink: async (data: InviteByLinkRequest): Promise<InvitationResponse> => {
    const res = await axiosInstance.post(`${BASE}/link`, data);
    return res.data;
  },

  // ── HR: Manage Invitations ────────────────────────────────────────────────

  listInvitations: async (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<InvitationListResponse> => {
    const res = await axiosInstance.get(BASE, { params });
    return res.data;
  },

  revokeInvitation: async (invitationId: string): Promise<void> => {
    await axiosInstance.delete(`${BASE}/${invitationId}`);
  },

  resendInvitation: async (invitationId: string): Promise<InvitationResponse> => {
    const res = await axiosInstance.post(`${BASE}/${invitationId}/resend`);
    return res.data;
  },

  // ── Employee: Validate & Accept ────────────────────────────────────────────

  // Public — no auth needed — check if token/code is valid
  validateInvite: async (params: {
    invite_token?: string;
    invite_code?: string;
  }): Promise<ValidateTokenResponse> => {
    const res = await axiosInstance.get(`${BASE}/validate`, { params });
    return res.data;
  },

  // Employee accepts invite → linked to employer
  acceptInvite: async (data: AcceptInviteRequest): Promise<AcceptInviteResponse> => {
    const res = await axiosInstance.post(`${BASE}/accept`, data);
    return res.data;
  },

  // ── HR: Manage Employees ──────────────────────────────────────────────────

  listEmployees: async (params?: {
    is_active?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<EmployeeListResponse> => {
    const res = await axiosInstance.get(`${BASE}/employees`, { params });
    return res.data;
  },

  updateEmployee: async (
    employeeLinkId: string,
    data: UpdateEmployeeRequest,
  ): Promise<void> => {
    await axiosInstance.patch(`${BASE}/employees/${employeeLinkId}`, data);
  },

  removeEmployee: async (employeeLinkId: string): Promise<void> => {
    await axiosInstance.delete(`${BASE}/employees/${employeeLinkId}`);
  },
};