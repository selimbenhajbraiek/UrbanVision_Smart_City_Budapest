export const BUDAPEST_CENTER: [number, number] = [47.4979, 19.0402];
export const DEFAULT_ZOOM = 13;
export const MIN_ZOOM = 10;
export const MAX_BOUNDS: [[number, number], [number, number]] = [
  [47.2, 18.6],
  [47.8, 19.6],
];

export type BaseMapId = "muted" | "osm" | "none";

export interface BaseMapConfig {
  label: string;
  url: string;
  attribution: string;
  maxZoom: number;
  /** CSS class on the tile layer (used to desaturate tiles in the browser). */
  className?: string;
}

const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// Both options use the official OpenStreetMap tile server (no API key; attribution required,
// light use only — fine for a university demonstration). "Muted" is the same tiles, just
// desaturated with CSS so BKK's coloured lines stand out (yellow trams vs. yellow OSM roads).
const OSM_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

export const BASE_MAPS: Record<Exclude<BaseMapId, "none">, BaseMapConfig> = {
  muted: {
    label: "OpenStreetMap (muted)",
    url: OSM_TILES,
    attribution: OSM_ATTRIBUTION,
    maxZoom: 19,
    className: "tiles-muted",
  },
  osm: {
    label: "OpenStreetMap (standard)",
    url: OSM_TILES,
    attribution: OSM_ATTRIBUTION,
    maxZoom: 19,
  },
};

export const BKK_ATTRIBUTION =
  'Timetable: <a href="https://bkk.hu/bkk-partnerek/egyeb/gtfs-menetrendi-adatok-programozoknak/">BKK GTFS</a>';
