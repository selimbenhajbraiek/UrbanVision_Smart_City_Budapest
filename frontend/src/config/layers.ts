import type { Mode } from "../api/types";
import type { Selection } from "../state";
import type { BaseMapId } from "./map";
import { TRANSIT_MODES } from "./transportModes";

export const URBAN_LAYER_STYLES: Record<string, { color: string; symbol: string }> = {
  ev_charging: { color: "#16a34a", symbol: "⚡" },
  bike_rental: { color: "#0891b2", symbol: "🚲" },
  park_and_ride: { color: "#9333ea", symbol: "P" },
};

export interface LayerState {
  baseMap: BaseMapId;
  stopModes: Mode[];
  routeModes: Mode[];
  weather: boolean;
  airQuality: boolean;
  urban: string[];
  vehicles: boolean;
}

// Bus/trolleybus lines are off by default: 335 overlapping lines would hide everything else.
// The muted base map is the default because BKK's yellow tram lines disappear among the
// yellow main roads of the standard OpenStreetMap style.
export const DEFAULT_LAYERS: LayerState = {
  baseMap: "muted",
  stopModes: [...TRANSIT_MODES],
  routeModes: ["metro", "hev", "tram", "boat"],
  weather: true,
  airQuality: true,
  urban: [],
  vehicles: false,
};

/** Number of enabled *data* layers (the base map is not counted). */
export function countActiveLayers(state: LayerState): number {
  return (
    (state.stopModes.length > 0 ? 1 : 0) +
    (state.routeModes.length > 0 ? 1 : 0) +
    (state.weather ? 1 : 0) +
    (state.airQuality ? 1 : 0) +
    state.urban.length +
    (state.vehicles ? 1 : 0)
  );
}

// --- URL hash (so a configured demo view can be bookmarked or shared) -------------------

const BASE_MAP_IDS: BaseMapId[] = ["muted", "osm", "none"];

function parseModes(value: string | null, fallback: Mode[]): Mode[] {
  if (value === null) return fallback;
  return value.split(",").filter((m): m is Mode => (TRANSIT_MODES as string[]).includes(m));
}

export function layersToHash(state: LayerState, selection: Selection | null = null): string {
  const params = new URLSearchParams({
    base: state.baseMap,
    stops: state.stopModes.join(","),
    routes: state.routeModes.join(","),
    weather: state.weather ? "1" : "0",
    air: state.airQuality ? "1" : "0",
    urban: state.urban.join(","),
    live: state.vehicles ? "1" : "0",
  });
  if (selection) params.set(selection.kind, selection.id);
  return `#${params.toString()}`;
}

/** The stop or route shown in the side panel, e.g. `#...&stop=F00954`. */
export function selectionFromHash(hash: string): Selection | null {
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  const stop = params.get("stop");
  if (stop) return { kind: "stop", id: stop };
  const route = params.get("route");
  if (route) return { kind: "route", id: route };
  return null;
}

export function layersFromHash(hash: string, knownUrbanLayers?: string[]): LayerState {
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  const base = params.get("base") as BaseMapId | null;
  const flag = (key: string, fallback: boolean) =>
    params.has(key) ? params.get(key) === "1" : fallback;
  const urbanIds = knownUrbanLayers ?? Object.keys(URBAN_LAYER_STYLES);
  return {
    baseMap: base && BASE_MAP_IDS.includes(base) ? base : DEFAULT_LAYERS.baseMap,
    stopModes: parseModes(params.get("stops"), DEFAULT_LAYERS.stopModes),
    routeModes: parseModes(params.get("routes"), DEFAULT_LAYERS.routeModes),
    weather: flag("weather", DEFAULT_LAYERS.weather),
    airQuality: flag("air", DEFAULT_LAYERS.airQuality),
    urban: (params.get("urban") ?? "").split(",").filter((id) => urbanIds.includes(id)),
    vehicles: flag("live", DEFAULT_LAYERS.vehicles),
  };
}

export function toggle<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item];
}
