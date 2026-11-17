import React, { useState } from "react";
import { Redirect } from "react-router-dom";

import LogoutButton from "../auth/LogoutButton";
import * as Routes from "../../constants/Routes";
import { useAuth } from "../../contexts/AuthContext";
import { homePathFor } from "../../utils/AuthUtils";

// POST /auth/register errors: 422 detail is a list (e.g. under 16), 409 is a string
const getRegisterErrorMessage = (error: unknown): string => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail) && detail[0]?.msg) {
    return String(detail[0].msg).replace(/^Value error, /, "");
  }
  return "Something went wrong. Please try again.";
};

// Shown once after sign-up: creates the user's profile with POST /auth/register
const CompleteProfilePage = (): React.ReactElement => {
  const { status, user, completeProfile } = useAuth();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === "loading") {
    return <div style={{ textAlign: "center" }}>Loading...</div>;
  }
  if (status === "signedOut") {
    return <Redirect to={Routes.LOGIN_PAGE} />;
  }
  if (status === "signedIn" && user) {
    return <Redirect to={homePathFor(user.role)} />;
  }

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await completeProfile({
        firstName,
        lastName,
        dateOfBirth: `${dateOfBirth}T00:00:00`,
        phoneNumber: phoneNumber || undefined,
      });
    } catch (e) {
      setError(getRegisterErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: "400px", margin: "40px auto" }}>
      <h1>Tell us about yourself</h1>
      <form onSubmit={onSubmit}>
        <div className="form-group">
          <label htmlFor="firstName" className="w-100">
            First name
            <input
              id="firstName"
              className="form-control"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              autoComplete="given-name"
              required
            />
          </label>
        </div>
        <div className="form-group">
          <label htmlFor="lastName" className="w-100">
            Last name
            <input
              id="lastName"
              className="form-control"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              autoComplete="family-name"
              required
            />
          </label>
        </div>
        <div className="form-group">
          <label htmlFor="dateOfBirth" className="w-100">
            Date of birth
            <input
              id="dateOfBirth"
              type="date"
              className="form-control"
              value={dateOfBirth}
              onChange={(e) => setDateOfBirth(e.target.value)}
              autoComplete="bday"
              required
            />
          </label>
        </div>
        <div className="form-group">
          <label htmlFor="phoneNumber" className="w-100">
            Phone number (optional)
            <input
              id="phoneNumber"
              type="tel"
              className="form-control"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              autoComplete="tel"
            />
          </label>
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        <button
          className="btn btn-primary btn-block"
          type="submit"
          disabled={submitting}
        >
          Continue
        </button>
      </form>
      <div className="mt-3">
        <LogoutButton />
      </div>
    </div>
  );
};

export default CompleteProfilePage;
