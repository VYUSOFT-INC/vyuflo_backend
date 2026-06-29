// src/hooks/usePayments.ts

import { useState, useEffect, useCallback } from "react";
import type {
  Fee,
  Payment,
  PaymentMethod,
  PaymentInvoice,
  PayFeeRequest,
  PayAllFeesRequest,
  AddPaymentMethodRequest,
} from "../../types/employee/payment.types";
import {
  listOutstandingFees,
  listPayments,
  listPaymentMethods,
  listInvoices,
  payFee,
  payAllFees,
  addPaymentMethod,
  deletePaymentMethod,
  setDefaultPaymentMethod,
} from "../../api/employee/payments.api";

// ── Outstanding Fees ──────────────────────────────────────────────────────────

export function useOutstandingFees() {
  const [fees, setFees] = useState<Fee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listOutstandingFees();
      setFees(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const totalDue = fees.reduce((sum, f) => sum + f.amount_usd, 0);

  return { fees, loading, error, refetch: fetch, totalDue };
}

// ── Payment History ───────────────────────────────────────────────────────────

export function usePaymentHistory() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listPayments();
      setPayments(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);
  return { payments, loading, error, refetch: fetch };
}

// ── Payment Methods ───────────────────────────────────────────────────────────

export function usePaymentMethods() {
  const [methods, setMethods] = useState<PaymentMethod[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listPaymentMethods();
      setMethods(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const defaultMethod = methods.find((m) => m.is_default) ?? methods[0] ?? null;

  return { methods, loading, error, refetch: fetch, defaultMethod };
}

// ── Invoices ──────────────────────────────────────────────────────────────────

export function useInvoices() {
  const [invoices, setInvoices] = useState<PaymentInvoice[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listInvoices();
      setInvoices(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);
  return { invoices, loading, error, refetch: fetch };
}

// ── Pay Fee ───────────────────────────────────────────────────────────────────

export function usePayFee(onSuccess?: () => void) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const submit = useCallback(
    async (body: PayFeeRequest) => {
      try {
        setLoading(true);
        setError(null);
        await payFee(body);
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

// ── Pay All Fees ──────────────────────────────────────────────────────────────

export function usePayAllFees(onSuccess?: () => void) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const submit = useCallback(
    async (body: PayAllFeesRequest) => {
      try {
        setLoading(true);
        setError(null);
        await payAllFees(body);
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

// ── Add Payment Method ────────────────────────────────────────────────────────

export function useAddPaymentMethod(onSuccess?: () => void) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const submit = useCallback(
    async (body: AddPaymentMethodRequest) => {
      try {
        setLoading(true);
        setError(null);
        await addPaymentMethod(body);
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

// ── Delete Payment Method ─────────────────────────────────────────────────────

export function useDeletePaymentMethod(onSuccess?: () => void) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const remove = useCallback(
    async (id: string) => {
      try {
        setLoading(true);
        setError(null);
        await deletePaymentMethod(id);
        onSuccess?.();
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [onSuccess]
  );

  return { remove, loading, error };
}

// ── Set Default Payment Method ────────────────────────────────────────────────

export function useSetDefaultPaymentMethod(onSuccess?: () => void) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const setDefault = useCallback(
    async (id: string) => {
      try {
        setLoading(true);
        setError(null);
        await setDefaultPaymentMethod(id);
        onSuccess?.();
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [onSuccess]
  );

  return { setDefault, loading, error };
}