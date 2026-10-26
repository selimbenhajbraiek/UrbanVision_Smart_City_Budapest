import { useCallback, useEffect, useState } from "react";
import type {
  AirQualityResponse,
  MetaResponse,
  RouteDetail,
  RouteSummary,
  StatsResponse,
  StopDetail,
  StopSearchResult,
  UrbanLayerInfo,
  WeatherResponse,
} from "./api/types";
import { StatsBar } from "./components/dashboard/StatsBar";
import { Header } from "./components/layout/Header";
import { MapView } from "./components/map/MapView";
import { AboutDialog } from "./components/panels/AboutDialog";
import { LayerPanel } from "./components/panels/LayerPanel";
import { RoutePanel } from "./components/panels/RoutePanel";
import { StopPanel } from "./components/panels/StopPanel";
import { WeatherCard } from "./components/panels/WeatherCard";
import {
  countActiveLayers,
  layersFromHash,
  layersToHash,
  selectionFromHash,
  type LayerState,
} from "./config/layers";
import { BUDAPEST_CENTER, DEFAULT_ZOOM } from "./config/map";
import { visibleStopModes, MODES } from "./config/transportModes";
import { useApi } from "./hooks/useApi";
import type { FlyTarget, Selection, Viewport } from "./state";
import { formatDate } from "./utils/format";

const WEATHER_REFRESH_MS = 10 * 60_000;
const STATS_REFRESH_MS = 5 * 60_000;

export default function App() {
  const [layers, setLayers] = useState<LayerState>(() => layersFromHash(window.location.hash));
  const [layersOpen, setLayersOpen] = useState(() => window.innerWidth > 900);
  const [aboutOpen, setAboutOpen] = useState(false);
  // Layers and the selected stop/route are restored from the URL, so demo views can be shared.
  const [selection, setSelection] = useState<Selection | null>(() =>
    selectionFromHash(window.location.hash),
  );
  const [fitRoute, setFitRoute] = useState(() => selection?.kind === "route");
  const [viewport, setViewport] = useState<Viewport | null>(null);
  const [flyTarget, setFlyTarget] = useState<FlyTarget | null>(null);
  // Stop to bring into view once its details have loaded (`animate: false` on first load).
  const [pendingFlyStop, setPendingFlyStop] = useState<{ id: string; animate: boolean } | null>(
    () => (selection?.kind === "stop" ? { id: selection.id, animate: false } : null),
  );

  useEffect(() => {
    window.history.replaceState(null, "", layersToHash(layers, selection));
  }, [layers, selection]);

  const meta = useApi<MetaResponse>("/api/meta");
  const stats = useApi<StatsResponse>("/api/stats", STATS_REFRESH_MS);
  const urbanLayers = useApi<UrbanLayerInfo[]>("/api/layers");
  const weather = useApi<WeatherResponse>(layers.weather ? "/api/weather" : null, WEATHER_REFRESH_MS);
  const airQuality = useApi<AirQualityResponse>(
    layers.airQuality ? "/api/air-quality" : null,
    WEATHER_REFRESH_MS,
  );

  const stopId = selection?.kind === "stop" ? selection.id : null;
  const routeId = selection?.kind === "route" ? selection.id : null;
  const stop = useApi<StopDetail>(stopId ? `/api/stops/${encodeURIComponent(stopId)}` : null);
  const route = useApi<RouteDetail>(routeId ? `/api/routes/${encodeURIComponent(routeId)}` : null);

  const flyTo = useCallback((target: Omit<FlyTarget, "key">) => {
    setFlyTarget({ ...target, key: Date.now() });
  }, []);

  const selectStop = useCallback((id: string) => setSelection({ kind: "stop", id }), []);
  const selectRoute = useCallback((id: string) => {
    setFitRoute(true);
    setSelection({ kind: "route", id });
  }, []);
  // Clicking a line on the map should not zoom away from where the user is looking.
  const selectRouteOnMap = useCallback((id: string) => {
    setFitRoute(false);
    setSelection({ kind: "route", id });
  }, []);

  // When a stop is chosen from a list (not the map), bring it into view.
  const selectStopAndFly = useCallback(
    (id: string) => {
      selectStop(id);
      setPendingFlyStop({ id, animate: true });
    },
    [selectStop],
  );
  useEffect(() => {
    if (pendingFlyStop && stop.data?.stop_id === pendingFlyStop.id) {
      flyTo({
        center: [stop.data.latitude, stop.data.longitude],
        zoom: 17,
        animate: pendingFlyStop.animate,
      });
      setPendingFlyStop(null);
    }
  }, [pendingFlyStop, stop.data, flyTo]);

  const pickSearchStop = (result: StopSearchResult) => {
    selectStop(result.stop_id);
    flyTo({ center: [result.latitude, result.longitude], zoom: 17 });
  };
  const pickSearchRoute = (result: RouteSummary) => selectRoute(result.route_id);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && !aboutOpen && setSelection(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [aboutOpen]);

  const activeLayers = countActiveLayers(layers);
  const hiddenModes =
    viewport === null
      ? []
      : layers.stopModes.filter((m) => !visibleStopModes([m], viewport.zoom).length);
  const feed = meta.data?.feed;

  return (
    <div className="app">
      <Header
        layersOpen={layersOpen}
        activeLayers={activeLayers}
        onToggleLayers={() => setLayersOpen((open) => !open)}
        onOpenAbout={() => setAboutOpen(true)}
        onResetView={() => flyTo({ center: BUDAPEST_CENTER, zoom: DEFAULT_ZOOM })}
        onPickStop={pickSearchStop}
        onPickRoute={pickSearchRoute}
      />

      <main className="main">
        <div className="map-area">
          <MapView
            layers={layers}
            urbanLayers={urbanLayers.data ?? []}
            realtimeEnabled={!!meta.data?.realtime.enabled}
            viewport={viewport}
            onViewportChange={setViewport}
            selectedStop={stopId && stop.data?.stop_id === stopId ? stop.data : null}
            selectedRoute={routeId && route.data?.route_id === routeId ? route.data : null}
            fitSelectedRoute={fitRoute}
            flyTarget={flyTarget}
            onSelectStop={selectStop}
            onSelectRoute={selectRouteOnMap}
          />

          {layersOpen && (
            <LayerPanel
              layers={layers}
              onChange={setLayers}
              urbanLayers={urbanLayers.data ?? []}
              realtime={meta.data?.realtime ?? null}
              zoom={viewport?.zoom ?? null}
              onClose={() => setLayersOpen(false)}
            />
          )}

          {(layers.weather || layers.airQuality) && (
            <WeatherCard
              weather={layers.weather ? weather : null}
              airQuality={layers.airQuality ? airQuality : null}
            />
          )}

          <div className="map-notices">
            {meta.error && <div className="notice notice-error">{meta.error}</div>}
            {feed && !feed.covers_today && (
              <div className="notice notice-warning">
                The imported timetable is valid {feed.valid_from && formatDate(feed.valid_from)} –{" "}
                {feed.valid_to && formatDate(feed.valid_to)}, not today. Re-import the BKK GTFS feed.
              </div>
            )}
            {meta.data && !feed && (
              <div className="notice notice-warning">
                No timetable imported yet. Run <code>python -m ingestion gtfs</code> in the backend.
              </div>
            )}
            {hiddenModes.length > 0 && (
              <div className="notice">
                Zoom in to see {hiddenModes.map((m) => MODES[m].label.toLowerCase()).join(", ")} stops
              </div>
            )}
          </div>
        </div>

        {selection?.kind === "stop" && (
          <StopPanel
            stopId={selection.id}
            stop={stop}
            onClose={() => setSelection(null)}
            onSelectStop={selectStopAndFly}
            onSelectRoute={selectRoute}
          />
        )}
        {selection?.kind === "route" && (
          <RoutePanel
            key={selection.id}
            routeId={selection.id}
            route={route}
            onClose={() => setSelection(null)}
            onSelectStop={selectStopAndFly}
          />
        )}
      </main>

      <StatsBar
        stats={stats.data}
        weather={layers.weather ? weather.data : null}
        meta={meta.data}
        activeLayers={activeLayers}
        error={stats.error}
      />

      {aboutOpen && <AboutDialog meta={meta.data} onClose={() => setAboutOpen(false)} />}
    </div>
  );
}
