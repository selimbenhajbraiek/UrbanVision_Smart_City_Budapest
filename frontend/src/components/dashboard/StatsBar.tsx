import type { MetaResponse, StatsResponse, WeatherResponse } from "../../api/types";
import { TRANSIT_MODES } from "../../config/transportModes";
import { formatDate, formatNumber } from "../../utils/format";
import { ModeBadge } from "../common/Badges";
import { Icon } from "../common/Icon";

interface Props {
  stats: StatsResponse | null;
  weather: WeatherResponse | null;
  meta: MetaResponse | null;
  activeLayers: number;
  error: string | null;
}

/** Simple dashboard strip with the key indicators of the city map. */
export function StatsBar({ stats, weather, meta, activeLayers, error }: Props) {
  const feed = stats?.feed;
  return (
    <footer className="stats-bar" aria-label="Dashboard">
      {error && (
        <div className="stat stat-error">
          <Icon name="alert" size={16} /> {error}
        </div>
      )}
      <Stat label="Mapped stops" value={stats ? formatNumber(stats.stops) : "–"} />
      <Stat label="Routes" value={stats ? formatNumber(stats.routes) : "–"} />
      <div className="stat">
        <span className="stat-label">Transport modes</span>
        <span className="stat-value">
          {stats?.transport_modes ?? "–"}
          <span className="mode-row">
            {TRANSIT_MODES.filter((m) => stats?.routes_by_mode[m]).map((mode) => (
              <ModeBadge key={mode} mode={mode} />
            ))}
          </span>
        </span>
      </div>
      <Stat label="Trips today" value={stats ? formatNumber(stats.trips_today) : "–"} />
      <Stat
        label="Weather now"
        value={weather ? `${Math.round(weather.current.temperature_c)}°C · ${weather.current.condition}` : "–"}
      />
      <Stat label="Active data layers" value={String(activeLayers)} />
      <div className={`stat ${feed && !feed.covers_today ? "stat-warning" : ""}`}>
        <span className="stat-label">Timetable valid</span>
        <span className="stat-value small">
          {feed?.valid_from && feed.valid_to
            ? `${formatDate(feed.valid_from)} – ${formatDate(feed.valid_to)}`
            : "not imported"}
        </span>
      </div>
      <div className="stat">
        <span className="stat-label">Real-time</span>
        <span className="stat-value small">
          {meta?.realtime.enabled ? (
            <>
              <span className="live-dot" /> live
            </>
          ) : (
            "off · scheduled data"
          )}
        </span>
      </div>
    </footer>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}
