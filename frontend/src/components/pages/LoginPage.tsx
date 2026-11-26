import React, { useState } from "react";
import { Link } from "react-router-dom";

import SignedInRedirect from "../auth/SignedInRedirect";
import * as Routes from "../../constants/Routes";
import { useAuth } from "../../contexts/AuthContext";
import { getAuthErrorMessage } from "../../utils/AuthUtils";

// Admins and attendees log in here; where they land depends on their role
const LoginPage = (): React.ReactElement => {
  const { logIn, logInWithGoogle, sessionError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
    run(() => logIn(email, password));
  };

  return (
    <div style={{ maxWidth: "400px", margin: "40px auto" }}>
      <SignedInRedirect />
      <h1>Log in</h1>
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
              autoComplete="current-password"
              required
            />
          </label>
        </div>
        {(error || sessionError) && (
          <div className="alert alert-danger">{error ?? sessionError}</div>
        )}
        <button
          className="btn btn-primary btn-block"
          type="submit"
          disabled={submitting}
        >
          Log in
        </button>
      </form>
      <button
        className="btn btn-outline-primary btn-block mt-2"
        type="button"
        onClick={() => run(logInWithGoogle)}
        disabled={submitting}
      >
        Continue with Google
      </button>
      <p className="mt-3">
        New here? <Link to={Routes.SIGNUP_PAGE}>Create an account</Link>
      </p>
    </div>
  );
};

export default LoginPage;
