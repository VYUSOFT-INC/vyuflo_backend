// src/hooks/useSelectAttorney.ts
import { useState, useEffect, useCallback, useRef } from "react";
import type { AxiosError } from "axios";
import type {
  AttorneyProfile,
  AttorneyFilters,
  UseAttorneysReturn,
  FetchAttorneysParams,
} from "../../types/employee/selectAttorney.types";
import { DEFAULT_FILTERS } from "../../types/employee/selectAttorney.types";
import { listAttorneys, getAttorney } from "../../api/employee/selectAttorney.api";

// =============================================================================
// Error helper (matches useApplications.ts pattern)
// =============================================================================

function extractMessage(e: unknown): string {
  const err = e as AxiosError<{ detail: string }>;
  return (
    err.response?.data?.detail ??
    (e instanceof Error ? e.message : "Something went wrong. Please try again.")
  );
}

// =============================================================================
// Filters → API params
// =============================================================================

function filtersToParams(f: AttorneyFilters): FetchAttorneysParams {
  return {
    zip_code:      f.zipCode      || undefined,
    radius_miles:  f.zipCode      ? f.radius : undefined,
    visa_types:    f.visaTypes.length    ? f.visaTypes    : undefined,
    languages:     f.languages.length   ? f.languages    : undefined,
    min_rating:    f.minRating    > 0    ? f.minRating    : undefined,
    max_fee_cents: f.maxFeeDollars != null ? f.maxFeeDollars * 100 : undefined,
    availability:  f.availability !== "All" ? f.availability : undefined,
    sort_by:       f.sortBy,
    page_size:     50,
  };
}

// =============================================================================
// useAttorneys — main list hook
// =============================================================================

export function useAttorneys(filters: AttorneyFilters): UseAttorneysReturn {
  const [attorneys, setAttorneys] = useState<AttorneyProfile[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [total, setTotal]         = useState(0);

  // Debounce ref — ZIP + radius changes wait 400 ms; all others are instant
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = filtersToParams(filters);
      const data   = await listAttorneys(params);
      setAttorneys(data.attorneys ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      console.error("Attorney list API error:", e);
      setError(extractMessage(e));
      setAttorneys([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [JSON.stringify(filters)]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const delay = filters.zipCode ? 400 : 0;
    debounceRef.current = setTimeout(() => { void load(); }, delay);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [load]);

  return { attorneys, loading, error, total, refetch: load };
}

// =============================================================================
// useAttorneyFilters — filter state management
// =============================================================================

export function useAttorneyFilters() {
  const [filters, setFilters] = useState<AttorneyFilters>(DEFAULT_FILTERS);

  const updateFilters = useCallback((partial: Partial<AttorneyFilters>) => {
    setFilters((prev) => ({ ...prev, ...partial }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  return { filters, updateFilters, resetFilters };
}

// =============================================================================
// useAttorney — single attorney by ID (for BookConsultation pre-fill)
// =============================================================================

export function useAttorney(attorneyId: string | undefined) {
  const [data, setData]         = useState<AttorneyProfile | null>(null);
  const [isLoading, setLoading] = useState(!!attorneyId);
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!attorneyId) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      setData(await getAttorney(attorneyId));
    } catch (e) {
      setError(extractMessage(e));
    } finally {
      setLoading(false);
    }
  }, [attorneyId]);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, refetch: load };
}