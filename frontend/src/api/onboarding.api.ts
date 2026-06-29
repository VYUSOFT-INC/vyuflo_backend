// import axios from "./axios";

// export const onboardingApi = {

//   getStatus: async () => {
//     const res = await axios.get("/onboarding/status");
//     return res.data;
//   },

//   verifyEmail: async (body: { otp: string }) => {
//     const res = await axios.post("/onboarding/verify-email", body);
//     return res.data; // { access_token, refresh_token, roles, onboarding_step }
//   },

//   resendOtp: async () => {
//     const res = await axios.post("/onboarding/resend-otp");
//     return res.data; // { message }
//   },

//   saveProfile: async (body: {
//     full_legal_name: string;
//     nationality: string;
//     visa_targets: string[];
//   }) => {
//     const res = await axios.post("/onboarding/profile", body);
//     return res.data;
//   },

//   complete: async () => {
//     const res = await axios.post("/onboarding/complete");
//     return res.data;
//   },

// };


// src/api/onboarding.api.ts
import axios from "./axios";
import type {
  OnboardingStatus,
  OnboardingProfileRequest,
  AttorneyProfileRequest,
  HRProfileRequest,
  AdminProfileRequest,
  OnboardingCompleteResponse,
} from "../types/onboarding.types";

export const onboardingApi = {

  getStatus: async (): Promise<OnboardingStatus> => {
    const res = await axios.get("/onboarding/status");
    return res.data;
  },

  verifyEmail: async (body: { otp: string }) => {
    const res = await axios.post("/onboarding/verify-email", body);
    return res.data;
  },

  resendOtp: async () => {
    const res = await axios.post("/onboarding/resend-otp");
    return res.data;
  },

  // Employee/Student
  saveProfile: async (body: OnboardingProfileRequest) => {
    const res = await axios.post("/onboarding/profile", body);
    return res.data;
  },

  // Attorney/Lawyer
  saveAttorneyProfile: async (body: AttorneyProfileRequest) => {
    const res = await axios.post("/onboarding/attorney-profile", body);
    return res.data;
  },

  // Employer/HR
  saveHRProfile: async (body: HRProfileRequest) => {
    const res = await axios.post("/onboarding/hr-profile", body);
    return res.data;
  },

  // App Admin
  saveAdminProfile: async (body: AdminProfileRequest) => {
    const res = await axios.post("/onboarding/admin-profile", body);
    return res.data;
  },

  complete: async (): Promise<OnboardingCompleteResponse> => {
    const res = await axios.post("/onboarding/complete");
    return res.data;
  },
};