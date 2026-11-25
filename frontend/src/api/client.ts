const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const TOKEN_KEY = "urbanvision.token";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ---------- Login token (kept in localStorage so a reload keeps you logged in) ----------

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage blocked (private mode): the session just won't survive a reload */
  }
}

// ---------- Requests ----------

async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      signal,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError("Cannot reach the UrbanVision API. Is the backend running?", 0);
  }
  if (!response.ok) {
    let detail = `Request failed (HTTP ${response.status})`;
    try {
      const json = await response.json();
      if (typeof json?.detail === "string") detail = json.detail;
      // FastAPI validation errors: a list of {msg, loc}
      else if (Array.isArray(json?.detail) && json.detail[0]?.msg) detail = json.detail[0].msg;
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** GET a JSON resource from the UrbanVision API. Errors carry the backend's `detail` text. */
export function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>("GET", path, undefined, signal);
}

export const postJson = <T>(path: string, body: unknown) => request<T>("POST", path, body);
export const patchJson = <T>(path: string, body: unknown) => request<T>("PATCH", path, body);
export const deleteJson = (path: string) => request<void>("DELETE", path);

/** Build a query string, skipping empty values. */
export function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}
