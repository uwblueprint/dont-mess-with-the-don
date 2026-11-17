import axios from "axios";

import baseAPIClient from "./BaseAPIClient";
import { AuthenticatedUser, RegisterRequest } from "../types/AuthTypes";

// The Firebase ID token is attached by baseAPIClient's request interceptor

// Resolves to null when the account has no profile yet (403)
const getMe = async (): Promise<AuthenticatedUser | null> => {
  try {
    const { data } = await baseAPIClient.get("/users/me");
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 403) {
      return null;
    }
    throw error;
  }
};

const register = async (
  profile: RegisterRequest,
): Promise<AuthenticatedUser> => {
  const { data } = await baseAPIClient.post("/auth/register", profile);
  return data;
};

export default { getMe, register };
