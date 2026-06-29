// src/api/profile.api.ts
import axios from "../axios";

export const profileApi = {

  // GET /users/me/profile
  getMyProfile: async () => {
    const res = await axios.get("/users/me/profile");
    return res.data;
  },
  // Add to profileApi object
  getLoginHistory: async (params?: { limit?: number; offset?: number }) => {
    const res = await axios.get("/users/me/login-history", { params });
    return res.data;
  },

  markSuspicious: async (historyId: string) => {
    const res = await axios.patch(`/users/me/login-history/${historyId}/suspicious`);
    return res.data;
  },

  signOutAllDevices: async () => {
    const res = await axios.post("/users/me/sign-out-all");
    return res.data;
  },

  uploadProfilePicture: async (file: File): Promise<{ profile_picture_url: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await axios.post("/users/me/upload-picture", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  },
  // PATCH /users/me/profile
  updateMyProfile: async (body: {
    full_legal_name?:      string;
    nationality?:          string;
    country_of_residence?: string;
    date_of_birth?:        string;
    gender?:               string;
    profile_picture_url?:  string;
    phone_number?:         string;
    country_code?:         string;
    timezone?:             string;
    preferred_language?:   string;
    onboarding_step?:      number;
    onboarding_completed?: boolean;

  }) => {
    const res = await axios.patch("/users/me/profile", body);
    return res.data;
  },
};

export const getMyProfile    = () => profileApi.getMyProfile();
export const updateMyProfile = (body: Parameters<typeof profileApi.updateMyProfile>[0]) =>
  profileApi.updateMyProfile(body);
export const getLoginHistory  = (params?: { limit?: number; offset?: number }) =>
  profileApi.getLoginHistory(params);
export const markSuspicious   = (historyId: string) =>
  profileApi.markSuspicious(historyId);
export const signOutAllDevices = () =>
  profileApi.signOutAllDevices();
export const uploadProfilePicture = (file: File) =>
  profileApi.uploadProfilePicture(file);