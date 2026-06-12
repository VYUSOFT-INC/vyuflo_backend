// src/hooks/useProfile.ts
import { useState, useEffect, useCallback } from "react";
import type { AxiosError } from "axios";
import { getLoginHistory, getMyProfile } from "../../api/employee/profile.api";

export interface UserProfile {
  id:                   string;
  user_id:              string;
  full_legal_name:      string | null;
  nationality:          string | null;
  country_of_residence: string | null;
  date_of_birth:        string | null;
  gender:               string | null;
  profile_picture_url:  string | null;
  timezone:             string | null;
  preferred_language:   string | null;
  phone_number:         string | null;   // ← ADD
  country_code:         string | null;   // ← ADD e.g. "+91"
  onboarding_step:      number;
  onboarding_completed: boolean;
  created_at:           string;
  updated_at:           string; 

}

function extractMessage(e: unknown): string {
  const err = e as AxiosError<{ detail: string }>;
  return (
    err.response?.data?.detail ??
    (e instanceof Error ? e.message : "Something went wrong.")
  );
}

export function useMyProfile() {
  const [data,      setData]    = useState<UserProfile | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [error,     setError]   = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getMyProfile());
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}



export function useLoginHistory(limit = 20) {
  const [data,      setData]    = useState<LoginHistoryResponse[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error,     setError]   = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getLoginHistory({ limit });
      setData(res.items ?? []);
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}

export interface LoginHistoryResponse {
  id:                 string;
  status:             "success" | "failed" | "blocked";
  auth_method:        string;
  ip_address:         string | null;
  city:               string | null;
  country:            string | null;
  browser:            string | null;
  os:                 string | null;
  device_type:        "desktop" | "mobile" | "tablet" | "unknown";
  failure_reason:     string | null;
  failed_attempts:    number;
  is_suspicious:      boolean;
  is_current_session: boolean;
  logged_out_at:      string | null;
  created_at:         string;
}