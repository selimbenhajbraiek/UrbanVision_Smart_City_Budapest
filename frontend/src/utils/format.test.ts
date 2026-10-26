import { describe, expect, it } from "vitest";
import {
  aqiColor,
  compassDirection,
  formatAge,
  formatClock,
  formatDistance,
  formatLocalHour,
  formatMinutesUntil,
} from "./format";

describe("formatting", () => {
  it("formats minutes until departure", () => {
    expect(formatMinutesUntil(0)).toBe("now");
    expect(formatMinutesUntil(7)).toBe("7 min");
    expect(formatMinutesUntil(60)).toBe("1 h");
    expect(formatMinutesUntil(75)).toBe("1 h 15 min");
  });

  it("shows clock times in Budapest time whatever the viewer's zone", () => {
    expect(formatClock("2026-10-05T06:00:00Z")).toBe("08:00");
    expect(formatClock("2026-10-06T00:30:00+02:00")).toBe("00:30");
  });

  it("extracts the hour from Open-Meteo local times", () => {
    expect(formatLocalHour("2026-09-27T19:00")).toBe("19:00");
  });

  it("formats distances", () => {
    expect(formatDistance(41)).toBe("41 m");
    expect(formatDistance(1520)).toBe("1.5 km");
    expect(formatDistance(null)).toBe("");
  });

  it("colours the air-quality index by band", () => {
    expect(aqiColor(10)).toBe("#10b981");
    expect(aqiColor(150)).toBe("#7e22ce");
  });

  it("converts bearings to compass points", () => {
    expect(compassDirection(0)).toBe("N");
    expect(compassDirection(359)).toBe("N");
    expect(compassDirection(135)).toBe("SE");
    expect(compassDirection(-90)).toBe("W");
  });

  it("formats how old a live position is", () => {
    const now = Date.parse("2026-09-29T10:00:00Z");
    expect(formatAge("2026-09-29T09:59:48Z", now)).toBe("12 s ago");
    expect(formatAge("2026-09-29T09:57:00Z", now)).toBe("3 min ago");
  });
});
