import type { ReactNode } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

/**
 * Shows its children only to admins. This is a convenience for the interface:
 * the real protection is the backend, which answers 401/403 on every /api/admin call.
 */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { user, checking } = useAuth();
  const location = useLocation();

  if (checking) return <div className="auth-page"><p className="muted">Checking your session…</p></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.role !== "admin") {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h2>Access denied</h2>
          <p className="muted">The admin dashboard is only available to administrators.</p>
          <Link to="/" className="primary-button">
            Back to the map
          </Link>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}
