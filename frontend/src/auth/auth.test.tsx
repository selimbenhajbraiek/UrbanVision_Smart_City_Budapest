import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getToken, setToken } from "../api/client";
import type { TokenResponse, User } from "../api/types";
import { LoginPage } from "../pages/LoginPage";
import { AuthProvider, useAuth } from "./AuthContext";
import { RequireAdmin } from "./RequireAdmin";

const admin: User = {
  id: 1,
  email: "admin@example.com",
  role: "admin",
  is_active: true,
  created_at: "2026-11-25T10:00:00Z",
  last_login_at: null,
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function WhoAmI() {
  const { user } = useAuth();
  return <p>{user ? `Hello ${user.email}` : "Anonymous"}</p>;
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<WhoAmI />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/admin"
            element={
              <RequireAdmin>
                <p>Secret admin area</p>
              </RequireAdmin>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("authentication", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    setToken(null);
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("logs in, stores the token and sends admins to the dashboard", async () => {
    const response: TokenResponse = {
      access_token: "token-123",
      token_type: "bearer",
      expires_in: 3600,
      user: admin,
    };
    fetchMock.mockResolvedValueOnce(jsonResponse(response));
    renderAt("/login");

    await userEvent.type(screen.getByLabelText("E-mail"), "admin@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "secret-password");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("Secret admin area")).toBeInTheDocument();
    expect(getToken()).toBe("token-123");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/login");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ email: "admin@example.com", password: "secret-password" });
  });

  it("shows the backend's error message on a failed login", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "Incorrect e-mail or password" }, 401));
    renderAt("/login");
    await userEvent.type(screen.getByLabelText("E-mail"), "x@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect e-mail or password");
    expect(getToken()).toBeNull();
  });

  it("restores the session from a stored token and sends it as a Bearer header", async () => {
    setToken("stored-token");
    fetchMock.mockResolvedValueOnce(jsonResponse(admin));
    renderAt("/");
    expect(await screen.findByText("Hello admin@example.com")).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe("Bearer stored-token");
  });

  it("forgets an expired token", async () => {
    setToken("expired-token");
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "Not authenticated" }, 401));
    renderAt("/");
    expect(await screen.findByText("Anonymous")).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it("redirects visitors from /admin to the login page", async () => {
    renderAt("/admin");
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
    expect(screen.queryByText("Secret admin area")).not.toBeInTheDocument();
  });

  it("refuses the admin page to normal users", async () => {
    setToken("user-token");
    fetchMock.mockResolvedValueOnce(jsonResponse({ ...admin, role: "user" }));
    renderAt("/admin");
    expect(await screen.findByText("Access denied")).toBeInTheDocument();
    expect(screen.queryByText("Secret admin area")).not.toBeInTheDocument();
  });
});
