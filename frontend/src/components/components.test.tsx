import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { StatsResponse, WeatherResponse } from "../api/types";
import { DataStatusBadge, RouteBadge } from "./common/Badges";
import { StatsBar } from "./dashboard/StatsBar";
import { WeatherCard } from "./panels/WeatherCard";

const stats: StatsResponse = {
  stops: 5644,
  stations: 196,
  routes: 389,
  trips: 282994,
  trips_today: 27809,
  transport_modes: 6,
  routes_by_mode: { bus: 319, tram: 44, trolleybus: 16, hev: 5, metro: 4, boat: 1 },
  stops_by_mode: {},
  urban_features: 0,
  feed: {
    publisher_name: "BKK",
    feed_version: "1",
    valid_from: "2026-09-27",
    valid_to: "2026-11-01",
    imported_at: "2026-09-27T17:00:00Z",
    covers_today: true,
  },
};

const weather: WeatherResponse = {
  location: { name: "Budapest", latitude: 47.5, longitude: 19.04 },
  current: {
    time: "2026-09-27T19:30",
    temperature_c: 21.2,
    apparent_temperature_c: 19.9,
    humidity_percent: 38,
    precipitation_mm: 0,
    weather_code: 3,
    condition: "Overcast",
    icon: "cloudy",
    is_day: false,
    wind_speed_kmh: 2.5,
    wind_direction_deg: 319,
    wind_direction: "NW",
    wind_gusts_kmh: 4.7,
  },
  hourly: [],
  source: "Open-Meteo",
  data_status: "model",
  fetched_at: "2026-09-27T17:31:00Z",
  attribution: "Weather data by Open-Meteo.com (CC BY 4.0)",
};

const loaded = <T,>(data: T) => ({ data, error: null, loading: false, reload: () => {} });

describe("StatsBar", () => {
  it("shows the key indicators", () => {
    render(<StatsBar stats={stats} weather={weather} meta={null} activeLayers={4} error={null} />);
    expect(screen.getByText("5,644")).toBeInTheDocument();
    expect(screen.getByText("389")).toBeInTheDocument();
    expect(screen.getByText("21°C · Overcast")).toBeInTheDocument();
    expect(screen.getByText("27 Sept 2026 – 1 Nov 2026")).toBeInTheDocument();
    expect(screen.getByText("off · scheduled data")).toBeInTheDocument();
  });

  it("shows API errors", () => {
    render(<StatsBar stats={null} weather={null} meta={null} activeLayers={0} error="API down" />);
    expect(screen.getByText("API down")).toBeInTheDocument();
  });
});

describe("WeatherCard", () => {
  it("renders temperature, wind and attribution", () => {
    render(<WeatherCard weather={loaded(weather)} airQuality={null} />);
    expect(screen.getByText("21°C")).toBeInTheDocument();
    expect(screen.getByText("3 km/h NW")).toBeInTheDocument();
    expect(screen.getByText(/Open-Meteo\.com/)).toBeInTheDocument();
    expect(screen.getByText("Model data")).toBeInTheDocument();
  });

  it("collapses when the summary is clicked", async () => {
    render(<WeatherCard weather={loaded(weather)} airQuality={null} />);
    await userEvent.click(screen.getByRole("button", { expanded: true }));
    expect(screen.queryByText("Feels like")).not.toBeInTheDocument();
  });
});

describe("badges", () => {
  it("uses BKK colours and handles clicks", async () => {
    const onClick = vi.fn();
    render(<RouteBadge shortName="M2" color="E41F18" textColor="FFFFFF" mode="metro" onClick={onClick} />);
    const badge = screen.getByRole("button", { name: "M2" });
    expect(badge).toHaveStyle({ background: "#E41F18" });
    await userEvent.click(badge);
    expect(onClick).toHaveBeenCalled();
  });

  it("labels scheduled data clearly", () => {
    render(<DataStatusBadge status="scheduled" />);
    expect(screen.getByText("Scheduled")).toHaveAttribute("title", expect.stringContaining("not live"));
  });
});
