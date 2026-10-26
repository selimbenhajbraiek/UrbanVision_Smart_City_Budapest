import type { DataStatus, Mode } from "../../api/types";
import { hexColor, MODES } from "../../config/transportModes";

export function ModeBadge({ mode }: { mode: Mode }) {
  return (
    <span className="mode-badge" style={{ background: MODES[mode].color }} title={MODES[mode].label}>
      {MODES[mode].shortLabel}
    </span>
  );
}

interface RouteBadgeProps {
  shortName: string | null;
  color: string | null;
  textColor: string | null;
  mode: Mode;
  onClick?: () => void;
  title?: string;
}

/** Line number in BKK's official colours, e.g. a yellow "4" for tram 4. */
export function RouteBadge({ shortName, color, textColor, mode, onClick, title }: RouteBadgeProps) {
  const style = {
    background: hexColor(color, MODES[mode].color),
    color: hexColor(textColor, "#ffffff"),
  };
  const label = shortName ?? "?";
  return onClick ? (
    <button type="button" className="route-badge" style={style} onClick={onClick} title={title}>
      {label}
    </button>
  ) : (
    <span className="route-badge" style={style} title={title}>
      {label}
    </span>
  );
}

const STATUS_TEXT: Record<DataStatus, { label: string; hint: string }> = {
  scheduled: { label: "Scheduled", hint: "From the official BKK timetable (GTFS), not live tracking" },
  realtime: { label: "Live", hint: "Real-time data from BKK FUTÁR" },
  model: { label: "Model data", hint: "Numerical weather/air-quality model output from Open-Meteo" },
  static: { label: "Static", hint: "Snapshot of OpenStreetMap data at import time" },
};

/** Makes the nature of every dataset explicit, so scheduled data is never mistaken for live. */
export function DataStatusBadge({ status }: { status: DataStatus }) {
  const { label, hint } = STATUS_TEXT[status];
  return (
    <span className={`status-badge status-${status}`} title={hint}>
      {status === "realtime" && <span className="live-dot" aria-hidden />}
      {label}
    </span>
  );
}
