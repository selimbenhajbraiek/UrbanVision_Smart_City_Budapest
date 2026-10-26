import { describe, expect, it } from "vitest";
import { hexColor, primaryMode, visibleStopModes } from "./transportModes";

describe("transport modes", () => {
  it("picks the most important mode of a stop", () => {
    expect(primaryMode(["bus", "metro"])).toBe("metro");
    expect(primaryMode(["bus", "tram"])).toBe("tram");
    expect(primaryMode([])).toBe("other");
  });

  it("hides bus stops when zoomed out", () => {
    expect(visibleStopModes(["metro", "tram", "bus"], 12)).toEqual(["metro"]);
    expect(visibleStopModes(["metro", "tram", "bus"], 14)).toEqual(["metro", "tram"]);
    expect(visibleStopModes(["metro", "tram", "bus"], 16)).toEqual(["metro", "tram", "bus"]);
  });

  it("validates GTFS colours", () => {
    expect(hexColor("FFD800")).toBe("#FFD800");
    expect(hexColor("nope", "#000000")).toBe("#000000");
    expect(hexColor(null, "#111111")).toBe("#111111");
  });
});
