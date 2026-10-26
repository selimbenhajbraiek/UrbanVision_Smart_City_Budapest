import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Vehicle } from "../../api/types";
import { VehiclePopup } from "./VehiclesLayer";

const tram: Vehicle = {
  vehicle_id: "V1",
  label: "Széll Kálmán tér",
  license_plate: "V-1234",
  wheelchair_accessible: true,
  in_service: true,
  trip_id: "T1",
  trip_in_timetable: true,
  route_id: "3040",
  route_short_name: "4",
  route_description: "Széll Kálmán tér M / Újbuda-központ M",
  mode: "tram",
  color: "FFD800",
  text_color: "000000",
  headsign: "Széll Kálmán tér M",
  final_stop: "Széll Kálmán tér M",
  next_stop_id: "S1",
  next_stop_name: "Oktogon M",
  current_status: "stopped_at",
  latitude: 47.5,
  longitude: 19.06,
  bearing: 90,
  speed_kmh: 0,
  timestamp: new Date().toISOString(),
};

describe("VehiclePopup", () => {
  it("says what the vehicle is and where it is going", () => {
    render(<VehiclePopup vehicle={tram} onSelectRoute={() => {}} onSelectStop={() => {}} />);
    expect(screen.getByText("Tram 4")).toBeInTheDocument();
    expect(screen.getByText("→ Széll Kálmán tér M")).toBeInTheDocument();
    expect(screen.getByText("Now at")).toBeInTheDocument();
    expect(screen.getByText("Oktogon M")).toBeInTheDocument();
    expect(screen.getByText("0 km/h · heading E")).toBeInTheDocument();
    expect(screen.getByText("Live")).toBeInTheDocument();
    // terminus equals headsign, so it is not repeated
    expect(screen.queryByText("Terminus")).not.toBeInTheDocument();
  });

  it("opens the line and the next stop", async () => {
    const onSelectRoute = vi.fn();
    const onSelectStop = vi.fn();
    render(<VehiclePopup vehicle={tram} onSelectRoute={onSelectRoute} onSelectStop={onSelectStop} />);
    await userEvent.click(screen.getByRole("button", { name: /whole line/ }));
    await userEvent.click(screen.getByRole("button", { name: "Oktogon M" }));
    expect(onSelectRoute).toHaveBeenCalledWith("3040");
    expect(onSelectStop).toHaveBeenCalledWith("S1");
  });

  it("is honest about trips missing from the BKK timetable", () => {
    const train: Vehicle = {
      ...tram,
      trip_in_timetable: false,
      route_id: null,
      route_short_name: null,
      mode: null,
      headsign: "Debrecen",
      next_stop_name: null,
    };
    render(<VehiclePopup vehicle={train} onSelectRoute={() => {}} onSelectStop={() => {}} />);
    expect(screen.getByText("→ Debrecen")).toBeInTheDocument();
    expect(screen.getByText(/not in the BKK timetable/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /whole line/ })).not.toBeInTheDocument();
  });
});
