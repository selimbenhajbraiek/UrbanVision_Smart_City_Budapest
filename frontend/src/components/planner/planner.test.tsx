import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Journey, PlanResponse } from "../../api/types";
import type { ApiState } from "../../hooks/useApi";
import { JourneyList } from "./JourneyList";
import { JourneySteps } from "./JourneySteps";
import { PlannerPanel } from "./PlannerPanel";

const deak = { name: "Deák Ferenc tér", latitude: 47.4979, longitude: 19.0546, stop_id: "F00954" };
const astoria = { name: "Astoria", latitude: 47.4935, longitude: 19.0605, stop_id: "F00955" };
const ors = { name: "Örs vezér tere", latitude: 47.503, longitude: 19.137, stop_id: "F00960" };

const metroJourney: Journey = {
  departure: "2026-11-25T08:00:00+01:00",
  arrival: "2026-11-25T08:14:00+01:00",
  duration_minutes: 14,
  transfers: 0,
  walking_minutes: 2,
  walking_m: 143,
  legs: [
    {
      kind: "walk",
      start: { name: "Home", latitude: 47.498, longitude: 19.054 },
      end: deak,
      departure: "2026-11-25T08:00:00+01:00",
      arrival: "2026-11-25T08:01:00+01:00",
      duration_minutes: 1,
      distance_m: 65,
      route: null,
      headsign: null,
      trip_id: null,
      stop_count: null,
      intermediate_stops: [],
      wheelchair_accessible: null,
      geometry: [
        [19.054, 47.498],
        [19.0546, 47.4979],
      ],
    },
    {
      kind: "transit",
      start: deak,
      end: ors,
      departure: "2026-11-25T08:01:00+01:00",
      arrival: "2026-11-25T08:13:00+01:00",
      duration_minutes: 12,
      distance_m: null,
      route: { route_id: "5200", short_name: "M2", mode: "metro", color: "E41F18", text_color: "FFFFFF" },
      headsign: "Örs vezér tere",
      trip_id: "T1",
      stop_count: 6,
      intermediate_stops: [astoria],
      wheelchair_accessible: true,
      geometry: [
        [19.0546, 47.4979],
        [19.137, 47.503],
      ],
    },
  ],
};

const walkJourney: Journey = {
  ...metroJourney,
  arrival: "2026-11-25T08:40:00+01:00",
  duration_minutes: 40,
  walking_minutes: 40,
  walking_m: 2400,
  legs: [{ ...metroJourney.legs[0], end: ors, duration_minutes: 40, distance_m: 2400 }],
};

describe("JourneyList", () => {
  it("summarises each option and marks the fastest", async () => {
    const onSelect = vi.fn();
    render(<JourneyList journeys={[metroJourney, walkJourney]} selected={0} onSelect={onSelect} />);
    const [first, second] = screen.getAllByRole("button");
    expect(within(first).getByText("14 min")).toBeInTheDocument();
    expect(within(first).getByText("M2")).toBeInTheDocument();
    expect(within(first).getByText(/No change/)).toBeInTheDocument();
    expect(within(first).getByText("Fastest")).toBeInTheDocument();
    expect(within(second).getByText("Walk only")).toBeInTheDocument();
    await userEvent.click(second);
    expect(onSelect).toHaveBeenCalledWith(1);
  });
});

describe("JourneySteps", () => {
  it("explains the trip step by step", () => {
    render(<JourneySteps journey={metroJourney} destination="Örs vezér tere" />);
    expect(screen.getByText(/Walk 1 min/)).toBeInTheDocument();
    expect(screen.getByText(/Metro M2/)).toBeInTheDocument();
    expect(screen.getByText("6 stops · 12 min", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Astoria")).toBeInTheDocument(); // intermediate stop
    expect(screen.getByText("Arrive at Örs vezér tere")).toBeInTheDocument();
  });
});

describe("PlannerPanel", () => {
  const idle: ApiState<PlanResponse> = { data: null, error: null, loading: false, reload: () => {} };
  const handlers = {
    onChange: vi.fn(),
    onSwap: vi.fn(),
    onWhenChange: vi.fn(),
    onPick: vi.fn(),
    onSelectJourney: vi.fn(),
    onClose: vi.fn(),
  };

  it("explains how to choose A and B, and can pick on the map", async () => {
    render(
      <PlannerPanel from={null} to={null} when={null} picking={null} plan={idle} selected={0} {...handlers} />,
    );
    expect(screen.getByText(/From here/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Choose to on the map" }));
    expect(handlers.onPick).toHaveBeenCalledWith("to");
  });

  it("shows the journeys and the steps of the selected one", () => {
    const plan: ApiState<PlanResponse> = {
      ...idle,
      data: {
        origin: { name: "Home", latitude: 47.498, longitude: 19.054 },
        destination: ors,
        requested_at: "2026-11-25T08:00:00+01:00",
        data_status: "scheduled",
        schedule_available: true,
        notice: null,
        journeys: [metroJourney],
      },
    };
    render(
      <PlannerPanel
        from={{ name: "Home", lat: 47.498, lon: 19.054 }}
        to={{ name: "Örs vezér tere", lat: 47.503, lon: 19.137 }}
        when={null}
        picking={null}
        plan={plan}
        selected={0}
        {...handlers}
      />,
    );
    expect(screen.getByText("Scheduled")).toBeInTheDocument();
    expect(screen.getByText("Step by step")).toBeInTheDocument();
    expect(screen.getByText("Arrive at Örs vezér tere")).toBeInTheDocument();
  });
});
