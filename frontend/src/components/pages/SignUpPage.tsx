import React, { useState } from "react";
import { Link } from "react-router-dom";

import SignedInRedirect from "../auth/SignedInRedirect";
import * as Routes from "../../constants/Routes";
import { useAuth } from "../../contexts/AuthContext";
import { getAuthErrorMessage } from "../../utils/AuthUtils";

// Attendee sign-up only; there is no admin sign-up. After the Firebase account
// is made, SignedInRedirect sends them on to the profile form
const SignUpPage = (): React.ReactElement => {
  const { signUp, logInWithGoogle } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const run = async (action: () => Promise<void>) => {
    setError(null);
    setSubmitting(true);
    try {
      await action();
    } catch (e) {
      setError(getAuthErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    run(() => signUp(email, password));
  };

  return (
    <div style={{ maxWidth: "400px", margin: "40px auto" }}>
      <SignedInRedirect />
      <h1>Create an account</h1>
      <form onSubmit={onSubmit}>
        <div className="form-group">
          <label htmlFor="email" className="w-100">
            Email
            <input
              id="email"
              type="email"
              className="form-control"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>
        </div>
        <div className="form-group">
          <label htmlFor="password" className="w-100">
            Password
            <input
              id="password"
              type="password"
              className="form-control"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              minLength={6}
              required
            />
          </label>
        </div>
        <div className="form-group">
          <label htmlFor="confirmPassword" className="w-100">
            Confirm password
            <input
              id="confirmPassword"
              type="password"
              className="form-control"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        <button
          className="btn btn-primary btn-block"
          type="submit"
          disabled={submitting}
        >
          Sign up
        </button>
      </form>
      <button
        className="btn btn-outline-primary btn-block mt-2"
        type="button"
        onClick={() => run(logInWithGoogle)}
        disabled={submitting}
      >
        Sign up with Google
      </button>
      <p className="mt-3">
        Already have an account? <Link to={Routes.LOGIN_PAGE}>Log in</Link>
      </p>
    </div>
  );
};

export default SignUpPage;
