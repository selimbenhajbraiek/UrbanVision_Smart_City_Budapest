import L from "leaflet";
import { useMemo } from "react";
import { Marker, Popup } from "react-leaflet";
import type { Vehicle, VehiclesResponse } from "../../api/types";
import { hexColor, MODES } from "../../config/transportModes";
import { useApi } from "../../hooks/useApi";
import { compassDirection, formatAge } from "../../utils/format";
import { DataStatusBadge, RouteBadge } from "../common/Badges";
import { Icon } from "../common/Icon";
import { escapeHtml } from "./StopsLayer";

const REFRESH_MS = 20_000;
const UNKNOWN_COLOR = "#475569";

interface Props {
  onSelectRoute: (routeId: string) => void;
  onSelectStop: (stopId: string) => void;
}

/** Live vehicle positions (only rendered when the backend has a BKK API key). */
export function VehiclesLayer({ onSelectRoute, onSelectStop }: Props) {
  const { data } = useApi<VehiclesResponse>("/api/realtime/vehicles", REFRESH_MS);
  if (!data) return null;
  return (
    <>
      {data.vehicles.map((vehicle) => (
        <VehicleMarker
          key={vehicle.vehicle_id}
          vehicle={vehicle}
          onSelectRoute={onSelectRoute}
          onSelectStop={onSelectStop}
        />
      ))}
    </>
  );
}

function vehicleColors(vehicle: Vehicle) {
  const fallback = vehicle.mode ? MODES[vehicle.mode].color : UNKNOWN_COLOR;
  return { background: hexColor(vehicle.color, fallback), text: hexColor(vehicle.text_color, "#ffffff") };
}

/** Line number in the line's colour, with an arrow pointing where the vehicle is heading. */
function vehicleIcon(vehicle: Vehicle): L.DivIcon {
  const { background, text } = vehicleColors(vehicle);
  const label = escapeHtml(vehicle.route_short_name ?? "•");
  const arrow =
    vehicle.bearing === null
      ? ""
      : `<span class="vehicle-arrow" style="transform: rotate(${Math.round(vehicle.bearing)}deg)"></span>`;
  return L.divIcon({
    className: "vehicle-icon",
    html: `${arrow}<span class="vehicle-badge" style="background:${background};color:${text}">${label}</span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -14],
  });
}

function VehicleMarker({ vehicle, onSelectRoute, onSelectStop }: { vehicle: Vehicle } & Props) {
  const icon = useMemo(
    () => vehicleIcon(vehicle),
    // Rebuild the icon only when something visible changes (not on every 20 s refresh).
    [vehicle.route_short_name, vehicle.color, vehicle.text_color, vehicle.bearing, vehicle.mode],
  );
  return (
    <Marker position={[vehicle.latitude, vehicle.longitude]} icon={icon}>
      {/* pane="popupPane": otherwise react-leaflet puts the popup in the vehicles pane,
          underneath other vehicle markers. */}
      <Popup minWidth={250} pane="popupPane">
        <VehiclePopup vehicle={vehicle} onSelectRoute={onSelectRoute} onSelectStop={onSelectStop} />
      </Popup>
    </Marker>
  );
}

const STATUS_TEXT: Record<NonNullable<Vehicle["current_status"]>, string> = {
  stopped_at: "Now at",
  incoming_at: "Arriving at",
  in_transit_to: "Next stop",
};

export function VehiclePopup({ vehicle, onSelectRoute, onSelectStop }: { vehicle: Vehicle } & Props) {
  const modeLabel = vehicle.mode ? MODES[vehicle.mode].label : "Vehicle";
  const nextStop = vehicle.next_stop_name;
  return (
    <div className="vehicle-popup">
      <div className="vehicle-popup-title">
        {vehicle.route_short_name && vehicle.mode ? (
          <RouteBadge
            shortName={vehicle.route_short_name}
            color={vehicle.color}
            textColor={vehicle.text_color}
            mode={vehicle.mode}
          />
        ) : null}
        <strong>
          {modeLabel} {vehicle.route_short_name ?? ""}
        </strong>
        <DataStatusBadge status="realtime" />
      </div>

      {vehicle.headsign && <div className="vehicle-headsign">→ {vehicle.headsign}</div>}

      <dl>
        {nextStop && vehicle.current_status && (
          <div>
            <dt>{STATUS_TEXT[vehicle.current_status]}</dt>
            <dd>
              {vehicle.next_stop_id ? (
                <button type="button" className="link-button" onClick={() => onSelectStop(vehicle.next_stop_id!)}>
                  {nextStop}
                </button>
              ) : (
                nextStop
              )}
            </dd>
          </div>
        )}
        {vehicle.final_stop && vehicle.final_stop !== vehicle.headsign && (
          <div>
            <dt>Terminus</dt>
            <dd>{vehicle.final_stop}</dd>
          </div>
        )}
        {vehicle.route_description && (
          <div>
            <dt>Line</dt>
            <dd>{vehicle.route_description}</dd>
          </div>
        )}
        <div>
          <dt>Speed</dt>
          <dd>
            {vehicle.speed_kmh !== null ? `${Math.round(vehicle.speed_kmh)} km/h` : "–"}
            {vehicle.bearing !== null && ` · heading ${compassDirection(vehicle.bearing)}`}
          </dd>
        </div>
        <div>
          <dt>Vehicle</dt>
          <dd>
            {vehicle.license_plate ?? vehicle.vehicle_id}
            {vehicle.wheelchair_accessible && (
              <Icon name="wheelchair" size={12} className="inline-icon" title="Wheelchair accessible" />
            )}
          </dd>
        </div>
      </dl>

      {!vehicle.trip_in_timetable && (
        <p className="vehicle-note">
          This trip is not in the BKK timetable (e.g. a MÁV national train), so only BKK's own
          destination label is known.
        </p>
      )}

      {vehicle.route_id && vehicle.trip_in_timetable && (
        <button type="button" className="vehicle-route-button" onClick={() => onSelectRoute(vehicle.route_id!)}>
          Show the whole line on the map
        </button>
      )}

      <p className="poi-source">
        Live position from BKK FUTÁR{vehicle.timestamp && ` · updated ${formatAge(vehicle.timestamp)}`}
      </p>
    </div>
  );
}
