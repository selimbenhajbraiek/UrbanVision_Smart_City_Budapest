import { useEffect, useState } from "react";
import { query } from "../../api/client";
import type { SearchResponse } from "../../api/types";
import type { PlannerPlace } from "../../state";
import { useApi } from "../../hooks/useApi";
import { ModeBadge } from "../common/Badges";
import { Icon } from "../common/Icon";

interface Props {
  label: "From" | "To";
  marker: "A" | "B";
  place: PlannerPlace | null;
  picking: boolean;
  onChange: (place: PlannerPlace | null) => void;
  onPickOnMap: () => void;
}

const DEBOUNCE_MS = 250;

/** A or B: type to search a stop, or choose a point on the map. */
export function PlaceInput({ label, marker, place, picking, onChange, onPickOnMap }: Props) {
  const [text, setText] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(text.trim()), DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [text]);

  const path = open && debounced.length >= 2 ? `/api/search${query({ q: debounced, limit: 6 })}` : null;
  const { data } = useApi<SearchResponse>(path);
  const stops = data && data.query === debounced ? data.stops : [];

  return (
    <div
      className="place-input"
      onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setOpen(false)}
    >
      <span className={`place-marker place-marker-${marker}`} aria-hidden>
        {marker}
      </span>
      {place ? (
        <div className="place-chosen">
          <span className="grow" title={place.name}>
            {place.name}
          </span>
          <button
            type="button"
            className="icon-button"
            aria-label={`Clear ${label.toLowerCase()}`}
            onClick={() => onChange(null)}
          >
            <Icon name="close" size={16} />
          </button>
        </div>
      ) : (
        <input
          type="search"
          aria-label={label}
          placeholder={picking ? "Click on the map…" : `${label}: search a stop`}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
        />
      )}
      <button
        type="button"
        className={`icon-button ${picking ? "active" : ""}`}
        title="Choose on the map"
        aria-label={`Choose ${label.toLowerCase()} on the map`}
        aria-pressed={picking}
        onClick={onPickOnMap}
      >
        <Icon name="pin" size={16} />
      </button>

      {open && !place && stops.length > 0 && (
        <div className="search-results place-results" role="listbox">
          {stops.map((stop) => (
            <button
              key={stop.stop_id}
              type="button"
              role="option"
              className="list-button"
              onClick={() => {
                onChange({ name: stop.name, lat: stop.latitude, lon: stop.longitude });
                setText("");
                setOpen(false);
              }}
            >
              <span className="grow">{stop.name}</span>
              {stop.modes.map((mode) => (
                <ModeBadge key={mode} mode={mode} />
              ))}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
