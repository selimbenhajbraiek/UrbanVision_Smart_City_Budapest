import { useState } from "react";
import type { RouteDetail } from "../../api/types";
import { MODES } from "../../config/transportModes";
import type { ApiState } from "../../hooks/useApi";
import { formatNumber } from "../../utils/format";
import { DataStatusBadge, RouteBadge } from "../common/Badges";
import { PanelMessage, SidePanel } from "./SidePanel";

interface Props {
  routeId: string;
  route: ApiState<RouteDetail>;
  onClose: () => void;
  onSelectStop: (stopId: string) => void;
}

export function RoutePanel({ routeId, route, onClose, onSelectStop }: Props) {
  const detail = route.data?.route_id === routeId ? route.data : null;
  const [directionIndex, setDirectionIndex] = useState(0);

  if (!detail) {
    return (
      <SidePanel title={route.error ? "Line not available" : "Loading line…"} onClose={onClose}>
        {route.error && <PanelMessage tone="error">{route.error}</PanelMessage>}
      </SidePanel>
    );
  }

  const direction = detail.directions[Math.min(directionIndex, detail.directions.length - 1)];

  return (
    <SidePanel
      title={`${MODES[detail.mode].label} ${detail.short_name ?? ""}`}
      onClose={onClose}
      subtitle={
        <>
          <RouteBadge
            shortName={detail.short_name}
            color={detail.color}
            textColor={detail.text_color}
            mode={detail.mode}
          />
          <span className="muted">{detail.description ?? detail.long_name}</span>
        </>
      }
    >
      <section className="panel-section">
        <dl className="facts">
          <div>
            <dt>Operator</dt>
            <dd>{detail.agency_name ?? "—"}</dd>
          </div>
          <div>
            <dt>Trips today</dt>
            <dd>
              {formatNumber(detail.trips_today)} <DataStatusBadge status="scheduled" />
            </dd>
          </div>
          <div>
            <dt>Route ID</dt>
            <dd>{detail.route_id}</dd>
          </div>
        </dl>
      </section>

      {direction ? (
        <section className="panel-section">
          {detail.directions.length > 1 && (
            <div className="tabs" role="tablist">
              {detail.directions.map((d, index) => (
                <button
                  key={d.direction_id}
                  type="button"
                  role="tab"
                  aria-selected={index === directionIndex}
                  className={index === directionIndex ? "tab active" : "tab"}
                  onClick={() => setDirectionIndex(index)}
                >
                  → {d.headsign ?? `Direction ${d.direction_id}`}
                </button>
              ))}
            </div>
          )}
          <ol className="stop-sequence" style={{ ["--line-color" as string]: `#${detail.color ?? "64748b"}` }}>
            {direction.stops.map((stop) => (
              <li key={`${stop.sequence}-${stop.stop_id}`}>
                <button type="button" className="link-button" onClick={() => onSelectStop(stop.stop_id)}>
                  {stop.name}
                </button>
              </li>
            ))}
          </ol>
          <p className="footnote">Stops of the most frequent trip pattern in each direction.</p>
        </section>
      ) : (
        <PanelMessage>No trips for this line in the current timetable.</PanelMessage>
      )}
    </SidePanel>
  );
}
