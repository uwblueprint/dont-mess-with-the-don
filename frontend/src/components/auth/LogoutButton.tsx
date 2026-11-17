import React from "react";

import { useAuth } from "../../contexts/AuthContext";

// Signing out sends every PrivateRoute back to the login page
const LogoutButton = (): React.ReactElement => {
  const { logOut } = useAuth();
  return (
    <button
      className="btn btn-outline-secondary"
      onClick={logOut}
      type="button"
    >
      Log out
    </button>
  );
};

export default LogoutButton;
