import { useCallback, useEffect, useState } from "react";
import { fetchJson } from "../api/client";

export interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/**
 * Fetch `path` whenever it changes (pass `null` to skip). Stale requests are aborted,
 * and `refreshMs` re-fetches periodically (e.g. departures every minute).
 * The previous data stays visible while a new request is loading.
 */
export function useApi<T>(path: string | null, refreshMs?: number): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => setReloadToken((n) => n + 1), []);

  useEffect(() => {
    if (!path) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    fetchJson<T>(path, controller.signal)
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch((err: Error) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [path, reloadToken]);

  useEffect(() => {
    if (!path || !refreshMs) return;
    const timer = window.setInterval(reload, refreshMs);
    return () => window.clearInterval(timer);
  }, [path, refreshMs, reload]);

  return { data, error, loading, reload };
}
