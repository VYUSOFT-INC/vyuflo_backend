
// src/api/payments.api.ts

import type {
  Fee,
  Payment,
  PaymentMethod,
  PaymentInvoice,
  PayFeeRequest,
  PayAllFeesRequest,
  AddPaymentMethodRequest,
} from "../../types/employee/payment.types";

import axios from "../axios";

export const paymentsApi = {
  // Fees
  listOutstandingFees: async (): Promise<Fee[]> => {
    const res = await axios.get("/fees/outstanding");
    return res.data.fees;
  },

  listAllFees: async (): Promise<Fee[]> => {
    const res = await axios.get("/fees");
    return res.data;
  },

  // Payments
  listPayments: async (): Promise<Payment[]> => {
    const res = await axios.get("/payments");
    return res.data;
  },

  payFee: async (body: PayFeeRequest): Promise<Payment> => {
    const res = await axios.post("/payments/pay-fee", body);
    return res.data;
  },

  payAllFees: async (body: PayAllFeesRequest): Promise<Payment> => {
    const res = await axios.post("/payments/pay-all", body);
    return res.data;
  },

  // Payment Methods
  listPaymentMethods: async (): Promise<PaymentMethod[]> => {
    const res = await axios.get("/payment-methods");
    return res.data;
  },

  addPaymentMethod: async (
    body: AddPaymentMethodRequest
  ): Promise<PaymentMethod> => {
    const res = await axios.post("/payment-methods", body);
    return res.data;
  },

  deletePaymentMethod: async (id: string): Promise<void> => {
    await axios.delete(`/payment-methods/${id}`);
  },

  setDefaultPaymentMethod: async (id: string): Promise<PaymentMethod> => {
    const res = await axios.patch(`/payment-methods/${id}/set-default`);
    return res.data;
  },

  // Invoices
  listInvoices: async (): Promise<PaymentInvoice[]> => {
    const res = await axios.get("/payment-invoices");
    return res.data;
  },
};

// Named exports
export const listOutstandingFees = () =>
  paymentsApi.listOutstandingFees();

export const listAllFees = () =>
  paymentsApi.listAllFees();

export const listPayments = () =>
  paymentsApi.listPayments();

export const payFee = (body: PayFeeRequest) =>
  paymentsApi.payFee(body);

export const payAllFees = (body: PayAllFeesRequest) =>
  paymentsApi.payAllFees(body);

export const listPaymentMethods = () =>
  paymentsApi.listPaymentMethods();

export const addPaymentMethod = (body: AddPaymentMethodRequest) =>
  paymentsApi.addPaymentMethod(body);

export const deletePaymentMethod = (id: string) =>
  paymentsApi.deletePaymentMethod(id);

export const setDefaultPaymentMethod = (id: string) =>
  paymentsApi.setDefaultPaymentMethod(id);

export const listInvoices = () =>
  paymentsApi.listInvoices();