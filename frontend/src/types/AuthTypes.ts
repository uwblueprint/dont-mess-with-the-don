export type UserRole = "attendee" | "admin";

// GET /users/me, camelized by baseAPIClient
export type AuthenticatedUser = {
  id: number;
  email: string | null;
  firstName: string | null;
  lastName: string | null;
  role: UserRole;
};

// POST /auth/register body; email comes from the Firebase token
export type RegisterRequest = {
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  phoneNumber?: string;
};

// loading: Firebase or /users/me hasn't answered yet
// needsProfile: signed in to Firebase but POST /auth/register hasn't been called
export type AuthStatus = "loading" | "signedOut" | "needsProfile" | "signedIn";
