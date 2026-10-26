const TIMEZONE = "Europe/Budapest";

/** "14:05" in Budapest time, regardless of the viewer's own time zone. */
export function formatClock(iso: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: TIMEZONE,
  }).format(new Date(iso));
}

/** Open-Meteo local times look like "2026-09-27T19:00" (already Budapest time). */
export function formatLocalHour(localIso: string): string {
  return localIso.slice(11, 16);
}

export function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${isoDate}T00:00:00Z`));
}

export function formatMinutesUntil(minutes: number): string {
  if (minutes <= 0) return "now";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-GB").format(value);
}

export function formatDistance(meters: number | null): string {
  if (meters === null) return "";
  return meters < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`;
}

export function round(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "–";
  return value.toFixed(digits);
}

/** Colour for the European Air Quality Index bands. */
export function aqiColor(value: number | null): string {
  if (value === null) return "#94a3b8";
  if (value <= 20) return "#10b981";
  if (value <= 40) return "#84cc16";
  if (value <= 60) return "#eab308";
  if (value <= 80) return "#f97316";
  if (value <= 100) return "#ef4444";
  return "#7e22ce";
}

const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

export function compassDirection(degrees: number): string {
  return COMPASS[Math.round((((degrees % 360) + 360) % 360) / 45) % 8];
}

/** "12 s ago", "3 min ago" relative to `now`. */
export function formatAge(iso: string, now: number = Date.now()): string {
  const seconds = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds} s ago`;
  return `${Math.floor(seconds / 60)} min ago`;
}
