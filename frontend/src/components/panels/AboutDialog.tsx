import { useEffect, useRef } from "react";
import type { MetaResponse } from "../../api/types";
import { formatDate } from "../../utils/format";
import { DataStatusBadge } from "../common/Badges";
import { Icon } from "../common/Icon";

interface Props {
  meta: MetaResponse | null;
  onClose: () => void;
}

/** Data sources, licences and attribution — required by OSM, Open-Meteo and good practice. */
export function AboutDialog({ meta, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal?.();
  }, []);

  return (
    <dialog ref={dialogRef} className="about-dialog" onClose={onClose} onCancel={onClose}>
      <header>
        <h2>About UrbanVision</h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close">
          <Icon name="close" />
        </button>
      </header>
      <p>
        UrbanVision is a university smart-city project that visualises open urban data for Budapest on
        a single interactive map. Team: Selim Ben Haj Braiek (project leader) and Nour Ounissi.
      </p>
      {meta?.feed && (
        <p>
          Timetable version <strong>{meta.feed.feed_version}</strong>, valid{" "}
          {meta.feed.valid_from && formatDate(meta.feed.valid_from)} –{" "}
          {meta.feed.valid_to && formatDate(meta.feed.valid_to)}.
        </p>
      )}
      <h3>Data sources &amp; licences</h3>
      <table className="sources">
        <thead>
          <tr>
            <th>Source</th>
            <th>Provides</th>
            <th>Licence</th>
            <th>Type</th>
          </tr>
        </thead>
        <tbody>
          {meta?.data_sources.map((source) => (
            <tr key={source.id}>
              <td>
                <a href={source.url} target="_blank" rel="noreferrer">
                  {source.name}
                </a>
                <div className="muted small">{source.attribution}</div>
              </td>
              <td>
                {source.provides}
                <div className="muted small">{source.update_frequency}</div>
              </td>
              <td>{source.license}</td>
              <td>
                <DataStatusBadge status={source.data_status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="footnote">
        <strong>Scheduled</strong> = official timetable, no live delays. <strong>Model</strong> = weather
        model output. <strong>Static</strong> = snapshot at import time. <strong>Live</strong> is only shown
        when a real-time feed is configured{meta && !meta.realtime.enabled ? " (currently off)" : ""}.
      </p>
    </dialog>
  );
}
