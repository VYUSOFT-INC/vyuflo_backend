import { useState, useEffect, useCallback } from "react";
import type {
  BookConsultationData,
  CreateConsultationBookingRequest,
} from "../../types/employee/bookConsultation.types";
import {
  getBookConsultationData,
  createConsultationBooking,
} from "../../api/employee/bookConsultation.api";

export function useBookConsultation(attorneyId?: string) {
  const [data, setData] = useState<BookConsultationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await getBookConsultationData(attorneyId);
      setData(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [attorneyId]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

export function useCreateConsultationBooking(onSuccess?: () => void) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(
    async (body: CreateConsultationBookingRequest) => {
      try {
        setLoading(true);
        setError(null);
        await createConsultationBooking(body);
        onSuccess?.();
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [onSuccess]
  );

  return { submit, loading, error };
}