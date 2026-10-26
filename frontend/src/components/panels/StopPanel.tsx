import type { DeparturesResponse, StopDetail } from "../../api/types";
import { primaryMode } from "../../config/transportModes";
import type { ApiState } from "../../hooks/useApi";
import { useApi } from "../../hooks/useApi";
import { formatClock, formatDistance, formatMinutesUntil } from "../../utils/format";
import { DataStatusBadge, ModeBadge, RouteBadge } from "../common/Badges";
import { Icon } from "../common/Icon";
import { PanelMessage, SidePanel } from "./SidePanel";

interface Props {
  stopId: string;
  stop: ApiState<StopDetail>;
  onClose: () => void;
  onSelectStop: (stopId: string) => void;
  onSelectRoute: (routeId: string) => void;
}

const DEPARTURES_REFRESH_MS = 60_000;

export function StopPanel({ stopId, stop, onClose, onSelectStop, onSelectRoute }: Props) {
  const detail = stop.data?.stop_id === stopId ? stop.data : null;

  if (!detail) {
    return (
      <SidePanel title={stop.error ? "Stop not available" : "Loading stop…"} onClose={onClose}>
        {stop.error && <PanelMessage tone="error">{stop.error}</PanelMessage>}
      </SidePanel>
    );
  }

  return (
    <SidePanel
      title={detail.name}
      onClose={onClose}
      subtitle={
        <>
          {detail.modes.map((mode) => (
            <ModeBadge key={mode} mode={mode} />
          ))}
          <span className="muted">
            Stop ID {detail.stop_id}
            {detail.stop_code && detail.stop_code !== detail.stop_id && ` · code ${detail.stop_code}`}
          </span>
          {detail.wheelchair_boarding === 1 && (
            <span className="muted" title="Wheelchair accessible">
              <Icon name="wheelchair" size={14} /> accessible
            </span>
          )}
        </>
      }
    >
      <section className="panel-section">
        <h3>Lines serving this stop</h3>
        {detail.routes.length === 0 ? (
          <p className="muted">No lines in the current timetable.</p>
        ) : (
          <div className="badge-row">
            {detail.routes.map((route) => (
              <RouteBadge
                key={route.route_id}
                shortName={route.short_name}
                color={route.color}
                textColor={route.text_color}
                mode={route.mode}
                title={route.description ?? undefined}
                onClick={() => onSelectRoute(route.route_id)}
              />
            ))}
          </div>
        )}
      </section>

      <Departures stopId={detail.stop_id} onSelectRoute={onSelectRoute} />

      {detail.nearby_platforms.length > 0 && (
        <section className="panel-section">
          <h3>Other platforms at this interchange</h3>
          <ul className="list">
            {detail.nearby_platforms.map((platform) => (
              <li key={platform.stop_id}>
                <button type="button" className="list-button" onClick={() => onSelectStop(platform.stop_id)}>
                  <ModeBadge mode={primaryMode(platform.modes)} />
                  <span className="grow">{platform.name}</span>
                  <span className="muted">{formatDistance(platform.distance_m)}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </SidePanel>
  );
}

function Departures({ stopId, onSelectRoute }: { stopId: string; onSelectRoute: (id: string) => void }) {
  const { data, error, loading, reload } = useApi<DeparturesResponse>(
    `/api/stops/${encodeURIComponent(stopId)}/departures?limit=15&minutes=120`,
    DEPARTURES_REFRESH_MS,
  );
  const current = data?.stop_id === stopId ? data : null;

  return (
    <section className="panel-section">
      <div className="section-heading">
        <h3>Next departures</h3>
        <DataStatusBadge status="scheduled" />
        <button type="button" className="icon-button small" onClick={reload} aria-label="Refresh departures" disabled={loading}>
          <Icon name="refresh" size={14} />
        </button>
      </div>
      {error && <PanelMessage tone="error">{error}</PanelMessage>}
      {!current && !error && <p className="muted">Loading departures…</p>}
      {current?.notice && <PanelMessage>{current.notice}</PanelMessage>}
      {current && current.departures.length > 0 && (
        <table className="departures">
          <tbody>
            {current.departures.map((departure) => (
              <tr key={`${departure.trip_id}-${departure.service_date}`}>
                <td className="departure-time">{formatClock(departure.departure_time)}</td>
                <td>
                  <RouteBadge
                    shortName={departure.route_short_name}
                    color={departure.color}
                    textColor={departure.text_color}
                    mode={departure.mode}
                    onClick={() => onSelectRoute(departure.route_id)}
                  />
                </td>
                <td className="grow">
                  {departure.headsign ?? "—"}
                  {departure.wheelchair_accessible && (
                    <Icon name="wheelchair" size={12} className="inline-icon" title="Accessible vehicle" />
                  )}
                </td>
                <td className="departure-in">{formatMinutesUntil(departure.minutes_until)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="footnote">
        Times come from the official BKK timetable (GTFS) and do not include live delays.
      </p>
    </section>
  );
}
