import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Switch } from "react-router-dom";

import PrivateRoute from "../PrivateRoute";
import * as Routes from "../../../constants/Routes";
import { useAuth } from "../../../contexts/AuthContext";
import { AuthStatus, UserRole } from "../../../types/AuthTypes";

jest.mock("../../../contexts/AuthContext", () => ({ useAuth: jest.fn() }));

const mockAuth = (status: AuthStatus, role?: UserRole) => {
  (useAuth as jest.Mock).mockReturnValue({
    status,
    user: role
      ? { id: 1, email: "a@example.com", firstName: "A", lastName: "B", role }
      : null,
  });
};

const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Switch>
        <Route path={Routes.LOGIN_PAGE} render={() => <div>login</div>} />
        <Route
          path={Routes.COMPLETE_PROFILE_PAGE}
          render={() => <div>complete profile</div>}
        />
        <PrivateRoute
          path={Routes.ADMIN_HOME_PAGE}
          allowedRole="admin"
          render={() => <div>admin home</div>}
        />
        <PrivateRoute
          path={Routes.ATTENDEE_HOME_PAGE}
          allowedRole="attendee"
          render={() => <div>attendee home</div>}
        />
      </Switch>
    </MemoryRouter>,
  );

describe("PrivateRoute", () => {
  it("sends signed-out users to login", () => {
    mockAuth("signedOut");
    renderAt(Routes.ADMIN_HOME_PAGE);
    expect(screen.getByText("login")).toBeInTheDocument();
  });

  it("sends users without a profile to the profile form", () => {
    mockAuth("needsProfile");
    renderAt(Routes.ATTENDEE_HOME_PAGE);
    expect(screen.getByText("complete profile")).toBeInTheDocument();
  });

  it("shows the page when the role matches", () => {
    mockAuth("signedIn", "admin");
    renderAt(Routes.ADMIN_HOME_PAGE);
    expect(screen.getByText("admin home")).toBeInTheDocument();
  });

  it("sends attendees away from admin pages to their own home", () => {
    mockAuth("signedIn", "attendee");
    renderAt(Routes.ADMIN_HOME_PAGE);
    expect(screen.getByText("attendee home")).toBeInTheDocument();
  });

  it("sends admins away from attendee pages to their own home", () => {
    mockAuth("signedIn", "admin");
    renderAt(Routes.ATTENDEE_HOME_PAGE);
    expect(screen.getByText("admin home")).toBeInTheDocument();
  });

  it("waits while auth is loading", () => {
    mockAuth("loading");
    renderAt(Routes.ADMIN_HOME_PAGE);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });
});
