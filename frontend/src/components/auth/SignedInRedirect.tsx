import React from "react";
import { Redirect, useLocation } from "react-router-dom";

import * as Routes from "../../constants/Routes";
import { useAuth } from "../../contexts/AuthContext";
import { homePathFor } from "../../utils/AuthUtils";

// On the login and sign-up pages: once someone is signed in, send them to the
// page they were trying to open, or else their home page
const SignedInRedirect = (): React.ReactElement | null => {
  const { status, user } = useAuth();
  const location = useLocation<
    { from?: { pathname: string; search: string } } | undefined
  >();

  if (status === "needsProfile") {
    return <Redirect to={Routes.COMPLETE_PROFILE_PAGE} />;
  }
  if (status === "signedIn" && user) {
    return <Redirect to={location.state?.from ?? homePathFor(user.role)} />;
  }
  return null;
};

export default SignedInRedirect;
