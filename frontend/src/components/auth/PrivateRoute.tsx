import React from "react";
import { Redirect, Route, RouteProps, useLocation } from "react-router-dom";

import * as Routes from "../../constants/Routes";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/AuthTypes";
import { homePathFor } from "../../utils/AuthUtils";

type PrivateRouteProps = RouteProps & {
  // Leave out to allow any signed-in user
  allowedRole?: UserRole;
};

// Redirects to login when signed out, to the profile form when the account has
// no profile yet, and to the user's own home page when they have the wrong role
const PrivateRoute = ({
  allowedRole,
  ...routeProps
}: PrivateRouteProps): React.ReactElement => {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <div style={{ textAlign: "center" }}>Loading...</div>;
  }
  if (status === "signedOut") {
    // Login sends them back here afterwards
    return (
      <Redirect
        to={{ pathname: Routes.LOGIN_PAGE, state: { from: location } }}
      />
    );
  }
  if (status === "needsProfile") {
    return <Redirect to={Routes.COMPLETE_PROFILE_PAGE} />;
  }
  if (allowedRole && user && user.role !== allowedRole) {
    return <Redirect to={homePathFor(user.role)} />;
  }
  // eslint-disable-next-line react/jsx-props-no-spreading
  return <Route {...routeProps} />;
};

export default PrivateRoute;
