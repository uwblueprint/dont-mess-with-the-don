import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { onAuthStateChanged, signOut } from "firebase/auth";

import LoginPage from "../LoginPage";
import AuthAPIClient from "../../../APIClients/AuthAPIClient";
import { AuthProvider } from "../../../contexts/AuthContext";

jest.mock("../../../firebase", () => ({}));
jest.mock("../../../APIClients/AuthAPIClient", () => ({ getMe: jest.fn() }));
jest.mock("firebase/auth", () => ({
  onAuthStateChanged: jest.fn(),
  signOut: jest.fn(),
}));

describe("LoginPage", () => {
  it("says the server couldn't be reached when /users/me fails", async () => {
    // Firebase reports a signed-in user, then getMe fails and we sign them out
    (onAuthStateChanged as jest.Mock).mockImplementation((_auth, callback) => {
      callback({ uid: "abc" });
      return () => {};
    });
    (AuthAPIClient.getMe as jest.Mock).mockRejectedValue(
      new Error("Network Error"),
    );

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(
      await screen.findByText("Couldn't reach the server. Please try again."),
    ).toBeInTheDocument();
    expect(signOut).toHaveBeenCalled();
  });
});
