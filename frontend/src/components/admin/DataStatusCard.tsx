import type { AdminDataStatus } from "../../api/types";
import { formatDate, formatDateTime, formatNumber } from "../../utils/format";

export function DataStatusCard({ status }: { status: AdminDataStatus }) {
  const { feed, days_until_expiry: days } = status;
  let level: "ok" | "warning" | "error" = "ok";
  let message = "Timetable is up to date.";
  if (!feed) {
    level = "error";
    message = "No timetable imported. Run: python -m ingestion gtfs";
  } else if (!feed.covers_today || (days !== null && days < 0)) {
    level = "error";
    message = "Timetable has expired. Re-import it: python -m ingestion gtfs";
  } else if (days !== null && days <= 7) {
    level = "warning";
    message = `Timetable ends in ${days} day${days === 1 ? "" : "s"}. Re-import soon.`;
  }

  return (
    <section className="admin-section">
      <h3>Data status</h3>
      <div className={`status-banner status-${level}`}>{message}</div>
      <table className="admin-table">
        <tbody>
          <tr>
            <th>BKK timetable</th>
            <td>
              {feed?.valid_from && feed.valid_to
                ? `${formatDate(feed.valid_from)} – ${formatDate(feed.valid_to)}`
                : "—"}
              {feed && <span className="muted"> · imported {formatDateTime(feed.imported_at)}</span>}
            </td>
          </tr>
          {status.layers.map((layer) => (
            <tr key={layer.id}>
              <th>{layer.title}</th>
              <td>
                {layer.imported_at ? (
                  <>
                    {formatNumber(layer.feature_count)} features
                    <span className="muted"> · imported {formatDateTime(layer.imported_at)}</span>
                  </>
                ) : (
                  <span className="muted">Not imported (python -m ingestion osm)</span>
                )}
              </td>
            </tr>
          ))}
          <tr>
            <th>Real-time</th>
            <td>{status.realtime_enabled ? "Enabled" : "Off (no BKK_API_KEY)"}</td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}
