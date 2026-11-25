import { useState } from "react";
import { deleteJson, patchJson } from "../../api/client";
import type { User } from "../../api/types";
import { formatDateTime } from "../../utils/format";

interface Props {
  users: User[];
  currentUserId: number;
  onChanged: () => void;
}

export function UsersTable({ users, currentUserId, onChanged }: Props) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  async function run(userId: number, action: () => Promise<unknown>) {
    setBusyId(userId);
    setError(null);
    try {
      await action();
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusyId(null);
      setConfirmDelete(null);
    }
  }

  return (
    <section className="admin-section">
      <h3>Users ({users.length})</h3>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>E-mail</th>
              <th>Role</th>
              <th>Status</th>
              <th>Created</th>
              <th>Last login</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const isMe = u.id === currentUserId;
              const busy = busyId === u.id;
              return (
                <tr key={u.id} className={u.is_active ? "" : "inactive"}>
                  <td>
                    {u.email}
                    {isMe && <span className="muted"> (you)</span>}
                  </td>
                  <td>
                    <span className={`role-badge role-${u.role}`}>{u.role}</span>
                  </td>
                  <td>{u.is_active ? "Active" : "Deactivated"}</td>
                  <td>{formatDateTime(u.created_at)}</td>
                  <td>{u.last_login_at ? formatDateTime(u.last_login_at) : "—"}</td>
                  <td className="row-actions">
                    {!isMe && (
                      <>
                        <button
                          type="button"
                          className="small-button"
                          disabled={busy}
                          onClick={() =>
                            run(u.id, () =>
                              patchJson(`/api/admin/users/${u.id}`, {
                                role: u.role === "admin" ? "user" : "admin",
                              }),
                            )
                          }
                        >
                          {u.role === "admin" ? "Make user" : "Make admin"}
                        </button>
                        <button
                          type="button"
                          className="small-button"
                          disabled={busy}
                          onClick={() =>
                            run(u.id, () =>
                              patchJson(`/api/admin/users/${u.id}`, { is_active: !u.is_active }),
                            )
                          }
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                        {confirmDelete === u.id ? (
                          <button
                            type="button"
                            className="small-button danger"
                            disabled={busy}
                            onClick={() => run(u.id, () => deleteJson(`/api/admin/users/${u.id}`))}
                          >
                            Confirm delete
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="small-button danger"
                            disabled={busy}
                            onClick={() => setConfirmDelete(u.id)}
                          >
                            Delete
                          </button>
                        )}
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
