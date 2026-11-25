"""SQL for user accounts. `password_hash` is only selected where a login needs it."""

from psycopg import Connection

PUBLIC_COLUMNS = "id, email, role, is_active, created_at, last_login_at"


def get_by_email_with_hash(conn: Connection, email: str) -> dict | None:
    return conn.execute(
        f"SELECT {PUBLIC_COLUMNS}, password_hash FROM users WHERE email = %s", (email,)
    ).fetchone()


def get_by_id(conn: Connection, user_id: int) -> dict | None:
    return conn.execute(f"SELECT {PUBLIC_COLUMNS} FROM users WHERE id = %s", (user_id,)).fetchone()


def email_exists(conn: Connection, email: str) -> bool:
    return conn.execute(
        "SELECT EXISTS (SELECT 1 FROM users WHERE email = %s) AS ok", (email,)
    ).fetchone()["ok"]


def create(conn: Connection, email: str, password_hash: str, role: str = "user") -> dict:
    return conn.execute(
        f"""
        INSERT INTO users (email, password_hash, role)
        VALUES (%s, %s, %s)
        RETURNING {PUBLIC_COLUMNS}
        """,
        (email, password_hash, role),
    ).fetchone()


def list_all(conn: Connection) -> list[dict]:
    return conn.execute(f"SELECT {PUBLIC_COLUMNS} FROM users ORDER BY created_at, id").fetchall()


def update(conn: Connection, user_id: int, role: str | None, is_active: bool | None) -> dict | None:
    return conn.execute(
        f"""
        UPDATE users
        SET role = COALESCE(%s, role), is_active = COALESCE(%s, is_active)
        WHERE id = %s
        RETURNING {PUBLIC_COLUMNS}
        """,
        (role, is_active, user_id),
    ).fetchone()


def set_password(conn: Connection, user_id: int, password_hash: str) -> None:
    conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))


def delete(conn: Connection, user_id: int) -> bool:
    return conn.execute("DELETE FROM users WHERE id = %s", (user_id,)).rowcount > 0


def touch_last_login(conn: Connection, user_id: int) -> None:
    conn.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (user_id,))


def count_active_admins(conn: Connection) -> int:
    return conn.execute(
        "SELECT count(*) AS n FROM users WHERE role = 'admin' AND is_active"
    ).fetchone()["n"]


def stats(conn: Connection) -> dict:
    return conn.execute(
        """
        SELECT count(*) AS total,
               count(*) FILTER (WHERE role = 'admin') AS admins,
               count(*) FILTER (WHERE is_active) AS active,
               count(*) FILTER (WHERE created_at > now() - interval '7 days') AS new_last_7_days,
               count(*) FILTER (WHERE last_login_at > now() - interval '7 days')
                   AS logins_last_7_days
        FROM users
        """
    ).fetchone()
