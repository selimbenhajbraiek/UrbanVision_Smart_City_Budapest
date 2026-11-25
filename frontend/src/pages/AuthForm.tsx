import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

interface Props {
  mode: "login" | "register";
}

/** Shared form for the login and register pages. */
export function AuthForm({ mode }: Props) {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!isLogin && password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const user = await (isLogin ? login : register)(email, password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from ?? (user.role === "admin" ? "/admin" : "/"), { replace: true });
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit} noValidate>
        <Link to="/" className="auth-brand">
          <img src="/favicon.svg" alt="" width={32} height={32} />
          <span>UrbanVision</span>
        </Link>
        <h2>{isLogin ? "Log in" : "Create an account"}</h2>

        <label className="field">
          <span>E-mail</span>
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label className="field">
          <span>Password{!isLogin && " (min. 8 characters)"}</span>
          <input
            type="password"
            autoComplete={isLogin ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={isLogin ? undefined : 8}
          />
        </label>
        {!isLogin && (
          <label className="field">
            <span>Repeat password</span>
            <input
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </label>
        )}

        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}

        <button type="submit" className="primary-button" disabled={busy || !email || !password}>
          {busy ? "Please wait…" : isLogin ? "Log in" : "Create account"}
        </button>

        <p className="muted auth-switch">
          {isLogin ? (
            <>
              No account yet? <Link to="/register">Create one</Link>
            </>
          ) : (
            <>
              Already registered? <Link to="/login">Log in</Link>
            </>
          )}
        </p>
        <p className="auth-switch">
          <Link to="/">← Back to the map</Link>
        </p>
      </form>
    </div>
  );
}
