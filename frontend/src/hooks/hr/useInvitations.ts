// src/hooks/useInvitations.ts
import { useState, useEffect, useCallback } from "react";
import { invitationApi } from "../../api/hr/invitation.api";
import type {
  InvitationResponse,
  EmployeeResponse,
  ValidateTokenResponse,
  InviteByEmailRequest,
  InviteByCodeRequest,
} from "../../types/hr/invitation.types";

// ── HR: List & manage invitations ─────────────────────────────────────────────

export function useMyInvitations(statusFilter?: string) {
  const [invitations, setInvitations] = useState<InvitationResponse[]>([]);
  const [total,       setTotal]       = useState(0);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await invitationApi.listInvitations({ status: statusFilter });
      setInvitations(res.items);
      setTotal(res.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load invitations.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { void load(); }, [load]);

  const revoke = async (invitationId: string) => {
    await invitationApi.revokeInvitation(invitationId);
    void load();
  };

  const resend = async (invitationId: string) => {
    await invitationApi.resendInvitation(invitationId);
    void load();
  };

  return { invitations, total, loading, error, refetch: load, revoke, resend };
}

// ── HR: Send email invite ─────────────────────────────────────────────────────

export function useSendEmailInvite() {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const send = async (data: InviteByEmailRequest) => {
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      await invitationApi.inviteByEmail(data);
      setSuccess(true);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Failed to send invite.");
    } finally {
      setLoading(false);
    }
  };

  return { send, loading, error, success, reset: () => { setSuccess(false); setError(null); } };
}

// ── HR: Generate company code ─────────────────────────────────────────────────

export function useGenerateCode() {
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState<string | null>(null);
  const [invitation,  setInvitation]  = useState<InvitationResponse | null>(null);

  const generate = async (data: InviteByCodeRequest = {}) => {
    setLoading(true);
    setError(null);
    try {
      const inv = await invitationApi.inviteByCode(data);
      setInvitation(inv);
      return inv;
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Failed to generate code.");
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { generate, invitation, loading, error };
}

// ── HR: List employees ────────────────────────────────────────────────────────

export function useMyEmployees(isActive = true) {
  const [employees, setEmployees] = useState<EmployeeResponse[]>([]);
  const [total,     setTotal]     = useState(0);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await invitationApi.listEmployees({ is_active: isActive });
      setEmployees(res.items);
      setTotal(res.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load employees.");
    } finally {
      setLoading(false);
    }
  }, [isActive]);

  useEffect(() => { void load(); }, [load]);

  const remove = async (employeeLinkId: string) => {
    await invitationApi.removeEmployee(employeeLinkId);
    void load();
  };

  return { employees, total, loading, error, refetch: load, remove };
}

// ── Employee: Validate invite token/code ──────────────────────────────────────

export function useValidateInvite(
  inviteToken?: string,
  inviteCode?: string,
) {
  const [result,  setResult]  = useState<ValidateTokenResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    if (!inviteToken && !inviteCode) return;
    const check = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await invitationApi.validateInvite({
          invite_token: inviteToken,
          invite_code:  inviteCode,
        });
        setResult(res);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to validate invite.");
      } finally {
        setLoading(false);
      }
    };
    void check();
  }, [inviteToken, inviteCode]);

  return { result, loading, error };
}

// ── Employee: Accept invite ───────────────────────────────────────────────────

export function useAcceptInvite() {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [company, setCompany] = useState<string | null>(null);

  const accept = async (inviteToken?: string, inviteCode?: string) => {
    if (!inviteToken && !inviteCode) {
      setError("Please provide an invite token or code.");
      return false;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await invitationApi.acceptInvite({
        invite_token: inviteToken,
        invite_code:  inviteCode,
      });
      setSuccess(true);
      setCompany(res.company_name);
      return true;
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Failed to accept invite.");
      return false;
    } finally {
      setLoading(false);
    }
  };

  return { accept, loading, error, success, company };
}