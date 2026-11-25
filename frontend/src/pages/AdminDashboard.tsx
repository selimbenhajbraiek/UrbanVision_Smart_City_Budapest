import { Link, useNavigate } from "react-router-dom";
import type { AdminDataStatus, AdminStats, User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AdminStatsCards } from "../components/admin/AdminStatsCards";
import { DataStatusCard } from "../components/admin/DataStatusCard";
import { UsersTable } from "../components/admin/UsersTable";
import { Icon } from "../components/common/Icon";
import { useApi } from "../hooks/useApi";

export function AdminDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const stats = useApi<AdminStats>("/api/admin/stats");
  const users = useApi<User[]>("/api/admin/users");
  const dataStatus = useApi<AdminDataStatus>("/api/admin/data-status");

  const refreshUsers = () => {
    users.reload();
    stats.reload();
  };
  const error = stats.error ?? users.error ?? dataStatus.error;

  return (
    <div className="admin-page">
      <header className="app-header">
        <div className="brand">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <div>
            <h1>UrbanVision</h1>
            <span>Admin dashboard</span>
          </div>
        </div>
        <nav className="header-actions">
          <Link to="/" className="header-button">
            <Icon name="map" /> <span className="label">Map</span>
          </Link>
          <span className="header-user" title={user?.email}>
            <Icon name="shield" /> <span className="label">{user?.email}</span>
          </span>
          <button
            type="button"
            className="header-button"
            onClick={() => {
              logout();
              navigate("/");
            }}
          >
            <Icon name="logout" /> <span className="label">Log out</span>
          </button>
        </nav>
      </header>

      <main className="admin-main">
        {error && <div className="form-error">{error}</div>}
        {stats.data ? <AdminStatsCards stats={stats.data} /> : !error && <p className="muted">Loading…</p>}
        <div className="admin-grid">
          {users.data && user && (
            <UsersTable users={users.data} currentUserId={user.id} onChanged={refreshUsers} />
          )}
          {dataStatus.data && <DataStatusCard status={dataStatus.data} />}
        </div>
      </main>
    </div>
  );
}
