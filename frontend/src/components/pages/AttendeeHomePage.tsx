import React from "react";

import LogoutButton from "../auth/LogoutButton";
import { useAuth } from "../../contexts/AuthContext";

// Placeholder landing page for attendees until their home page is built
const AttendeeHomePage = (): React.ReactElement => {
  const { user } = useAuth();
  return (
    <div style={{ textAlign: "center", paddingTop: "20px" }}>
      <h1>Welcome, {user?.firstName}</h1>
      <LogoutButton />
    </div>
  );
};

export default AttendeeHomePage;
