import React from "react";

import LogoutButton from "../auth/LogoutButton";
import { useAuth } from "../../contexts/AuthContext";

// Placeholder landing page for admins until the admin dashboard is built
const AdminHomePage = (): React.ReactElement => {
  const { user } = useAuth();
  return (
    <div style={{ textAlign: "center", paddingTop: "20px" }}>
      <h1>Admin</h1>
      <p>Signed in as {user?.email}</p>
      <LogoutButton />
    </div>
  );
};

export default AdminHomePage;
