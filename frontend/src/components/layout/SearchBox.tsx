import { useEffect, useState } from "react";
import { query } from "../../api/client";
import type { RouteSummary, SearchResponse, StopSearchResult } from "../../api/types";
import { useApi } from "../../hooks/useApi";
import { ModeBadge, RouteBadge } from "../common/Badges";
import { Icon } from "../common/Icon";

interface Props {
  onPickStop: (stop: StopSearchResult) => void;
  onPickRoute: (route: RouteSummary) => void;
}

const DEBOUNCE_MS = 250;

export function SearchBox({ onPickStop, onPickRoute }: Props) {
  const [text, setText] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(text.trim()), DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [text]);

  const path = debounced.length >= 2 ? `/api/search${query({ q: debounced, limit: 6 })}` : null;
  const { data, error } = useApi<SearchResponse>(path);
  const results = data && data.query === debounced ? data : null;
  const hasResults = !!results && (results.stops.length > 0 || results.routes.length > 0);

  const reset = () => {
    setText("");
    setOpen(false);
  };
  const pickStop = (stop: StopSearchResult) => {
    onPickStop(stop);
    reset();
  };
  const pickRoute = (route: RouteSummary) => {
    onPickRoute(route);
    reset();
  };

  return (
    <div className="search" onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setOpen(false)}>
      <Icon name="search" size={16} className="search-icon" />
      <input
        type="search"
        placeholder="Search stops or lines (e.g. Deák, 4, M2)"
        value={text}
        aria-label="Search stops or lines"
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Escape") reset();
          if (e.key === "Enter" && results) {
            if (results.routes[0] && results.routes[0].short_name?.toLowerCase() === debounced.toLowerCase())
              pickRoute(results.routes[0]);
            else if (results.stops[0]) pickStop(results.stops[0]);
            else if (results.routes[0]) pickRoute(results.routes[0]);
          }
        }}
      />
      {open && path && (
        <div className="search-results" role="listbox">
          {error && <div className="search-empty">{error}</div>}
          {results && !hasResults && <div className="search-empty">No matches for “{debounced}”.</div>}
          {results && results.routes.length > 0 && (
            <div className="search-group">
              <div className="search-group-title">Lines</div>
              <div className="badge-row">
                {results.routes.map((route) => (
                  <RouteBadge
                    key={route.route_id}
                    shortName={route.short_name}
                    color={route.color}
                    textColor={route.text_color}
                    mode={route.mode}
                    title={route.description ?? undefined}
                    onClick={() => pickRoute(route)}
                  />
                ))}
              </div>
            </div>
          )}
          {results && results.stops.length > 0 && (
            <div className="search-group">
              <div className="search-group-title">Stops</div>
              {results.stops.map((stop) => (
                <button
                  key={stop.stop_id}
                  type="button"
                  className="list-button"
                  role="option"
                  onClick={() => pickStop(stop)}
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
      )}
    </div>
  );
}
