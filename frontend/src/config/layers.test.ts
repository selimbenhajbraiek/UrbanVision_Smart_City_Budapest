import { describe, expect, it } from "vitest";
import {
  countActiveLayers,
  DEFAULT_LAYERS,
  layersFromHash,
  layersToHash,
  selectionFromHash,
  toggle,
} from "./layers";

describe("layer state", () => {
  it("round-trips through the URL hash", () => {
    const state = {
      ...DEFAULT_LAYERS,
      baseMap: "none" as const,
      routeModes: ["bus" as const],
      urban: ["ev_charging"],
      airQuality: false,
    };
    expect(layersFromHash(layersToHash(state))).toEqual(state);
  });

  it("falls back to defaults for an empty hash", () => {
    expect(layersFromHash("")).toEqual(DEFAULT_LAYERS);
  });

  it("ignores unknown values from a hand-edited URL", () => {
    const state = layersFromHash("#base=satellite&stops=metro,rocket&urban=unicorns,bike_rental");
    expect(state.baseMap).toBe(DEFAULT_LAYERS.baseMap);
    expect(state.stopModes).toEqual(["metro"]);
    expect(state.urban).toEqual(["bike_rental"]);
  });

  it("allows switching every mode off", () => {
    expect(layersFromHash("#stops=&routes=").stopModes).toEqual([]);
  });

  it("counts active data layers without the base map", () => {
    expect(countActiveLayers(DEFAULT_LAYERS)).toBe(4); // stops, routes, weather, air quality
    expect(countActiveLayers({ ...DEFAULT_LAYERS, stopModes: [], urban: ["a", "b"] })).toBe(5);
  });

  it("stores the selected stop or route in the hash", () => {
    const hash = layersToHash(DEFAULT_LAYERS, { kind: "stop", id: "F00954" });
    expect(selectionFromHash(hash)).toEqual({ kind: "stop", id: "F00954" });
    expect(selectionFromHash(layersToHash(DEFAULT_LAYERS, { kind: "route", id: "5300" }))).toEqual({
      kind: "route",
      id: "5300",
    });
    expect(selectionFromHash(layersToHash(DEFAULT_LAYERS))).toBeNull();
  });

  it("toggles list items", () => {
    expect(toggle(["a", "b"], "a")).toEqual(["b"]);
    expect(toggle(["a"], "b")).toEqual(["a", "b"]);
  });
});
