/** What the side panel is showing. */
export type Selection = { kind: "stop"; id: string } | { kind: "route"; id: string };

/** A request to move the map. `key` makes repeated requests to the same place work. */
export interface FlyTarget {
  key: number;
  center?: [number, number];
  zoom?: number;
  bounds?: [[number, number], [number, number]];
  /** false = jump without animation (used when restoring a view from the URL). */
  animate?: boolean;
}

export interface Viewport {
  /** [minLon, minLat, maxLon, maxLat] */
  bbox: [number, number, number, number];
  zoom: number;
}
