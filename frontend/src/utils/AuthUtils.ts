import { FirebaseError } from "firebase/app";

import * as Routes from "../constants/Routes";
import { UserRole } from "../types/AuthTypes";

export const homePathFor = (role: UserRole): string =>
  role === "admin" ? Routes.ADMIN_HOME_PAGE : Routes.ATTENDEE_HOME_PAGE;

const FIREBASE_ERROR_MESSAGES: Record<string, string> = {
  // Firebase also returns this for accounts that only sign in with Google
  "auth/invalid-credential":
    "Incorrect email or password. If you signed up with Google, use Continue with Google.",
  "auth/invalid-email": "Enter a valid email address.",
  "auth/email-already-in-use": "An account with this email already exists.",
  "auth/weak-password": "Password must be at least 6 characters.",
  "auth/too-many-requests": "Too many attempts. Try again in a few minutes.",
  "auth/popup-closed-by-user": "Google sign-in was closed before finishing.",
};

// A message to show on the login and sign-up forms
export const getAuthErrorMessage = (error: unknown): string => {
  if (error instanceof FirebaseError) {
    return (
      FIREBASE_ERROR_MESSAGES[error.code] ??
      "Something went wrong. Please try again."
    );
  }
  return "Something went wrong. Please try again.";
};
