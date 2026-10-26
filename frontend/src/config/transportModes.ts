import type { Mode } from "../api/types";

export interface ModeConfig {
  label: string;
  shortLabel: string;
  /** Stop marker colour (route lines use BKK's official colour from GTFS instead). */
  color: string;
  /** Stops of this mode are only drawn from this zoom level on, to avoid clutter. */
  minStopZoom: number;
  /** Line width of route geometry. */
  lineWeight: number;
}

// Order = visual priority (a stop served by metro and bus is drawn as a metro stop).
export const MODES: Record<Mode, ModeConfig> = {
  metro: { label: "Metro", shortLabel: "M", color: "#1d4ed8", minStopZoom: 11, lineWeight: 6 },
  hev: { label: "HÉV (suburban rail)", shortLabel: "HÉV", color: "#15803d", minStopZoom: 11, lineWeight: 5 },
  rail: { label: "Railway", shortLabel: "Rail", color: "#475569", minStopZoom: 11, lineWeight: 5 },
  tram: { label: "Tram", shortLabel: "Tram", color: "#eab308", minStopZoom: 14, lineWeight: 3.5 },
  trolleybus: { label: "Trolleybus", shortLabel: "Trolley", color: "#dc2626", minStopZoom: 15, lineWeight: 2.5 },
  bus: { label: "Bus", shortLabel: "Bus", color: "#0284c7", minStopZoom: 15, lineWeight: 2 },
  boat: { label: "Boat", shortLabel: "Boat", color: "#7c3aed", minStopZoom: 11, lineWeight: 3.5 },
  other: { label: "Other", shortLabel: "Other", color: "#64748b", minStopZoom: 15, lineWeight: 2 },
};

/** The modes that actually appear in the BKK feed, in display order. */
export const TRANSIT_MODES: Mode[] = ["metro", "hev", "tram", "trolleybus", "bus", "boat"];

const PRIORITY = Object.keys(MODES) as Mode[];

export function primaryMode(modes: Mode[]): Mode {
  return PRIORITY.find((mode) => modes.includes(mode)) ?? "other";
}

/** Modes whose stops are visible at the given zoom level. */
export function visibleStopModes(enabled: Mode[], zoom: number): Mode[] {
  return enabled.filter((mode) => zoom >= MODES[mode].minStopZoom);
}

export function hexColor(color: string | null | undefined, fallback = "#64748b"): string {
  return color && /^[0-9A-Fa-f]{6}$/.test(color) ? `#${color}` : fallback;
}
