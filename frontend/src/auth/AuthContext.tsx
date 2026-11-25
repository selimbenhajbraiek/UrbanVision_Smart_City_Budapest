import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, fetchJson, getToken, postJson, setToken } from "../api/client";
import type { TokenResponse, User } from "../api/types";

interface AuthState {
  /** The logged-in user, or null. */
  user: User | null;
  /** True while a stored token is being checked on start-up. */
  checking: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(() => getToken() !== null);

  // On start-up, ask the backend whether the stored token is still valid.
  useEffect(() => {
    if (!getToken()) return;
    const controller = new AbortController();
    fetchJson<User>("/api/auth/me", controller.signal)
      .then(setUser)
      .catch((err: Error) => {
        if (err.name === "AbortError") return;
        // Expired or revoked: forget it. (Network errors keep the token for a later try.)
        if (err instanceof ApiError && err.status === 401) setToken(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setChecking(false);
      });
    return () => controller.abort();
  }, []);

  const startSession = useCallback((response: TokenResponse) => {
    setToken(response.access_token);
    setUser(response.user);
    return response.user;
  }, []);

  const login = useCallback(
    async (email: string, password: string) =>
      startSession(await postJson<TokenResponse>("/api/auth/login", { email, password })),
    [startSession],
  );

  const register = useCallback(
    async (email: string, password: string) =>
      startSession(await postJson<TokenResponse>("/api/auth/register", { email, password })),
    [startSession],
  );

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, checking, login, register, logout }),
    [user, checking, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
