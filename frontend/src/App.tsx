import { useCallback, useEffect, useRef, useState } from "react";
import { fetchJson, query } from "./api/client";
import type {
  AirQualityResponse,
  MetaResponse,
  PlanResponse,
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
import { PlannerPanel, type PlannerTime } from "./components/planner/PlannerPanel";
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
import type { FlyTarget, PlannerField, PlannerPlace, Selection, Viewport } from "./state";
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

  // ---- Route planner ----
  const [plannerOpen, setPlannerOpen] = useState(false);
  const [planFrom, setPlanFrom] = useState<PlannerPlace | null>(null);
  const [planTo, setPlanTo] = useState<PlannerPlace | null>(null);
  const [planWhen, setPlanWhen] = useState<PlannerTime | null>(null); // null = leave now
  const [picking, setPicking] = useState<PlannerField | null>(null);
  const [journeyIndex, setJourneyIndex] = useState(0);
  const lastStopClick = useRef(0);

  useEffect(() => {
    // Keep history.state: React Router stores its navigation data there.
    window.history.replaceState(window.history.state, "", layersToHash(layers, selection));
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

  const planPath =
    plannerOpen && planFrom && planTo
      ? `/api/plan${query({
          from: `${planFrom.lat.toFixed(6)},${planFrom.lon.toFixed(6)}`,
          to: `${planTo.lat.toFixed(6)},${planTo.lon.toFixed(6)}`,
          from_name: planFrom.name,
          to_name: planTo.name,
          date: planWhen?.date,
          time: planWhen?.time,
        })}`
      : null;
  const plan = useApi<PlanResponse>(planPath);
  const planResult = planPath && plan.data ? plan.data : null;
  const journey = planResult?.journeys[journeyIndex] ?? null;

  useEffect(() => setJourneyIndex(0), [planPath]);

  // Show the whole selected journey (or A and B while there is none yet).
  useEffect(() => {
    if (!plannerOpen) return;
    const points: [number, number][] = journey
      ? journey.legs.flatMap((leg) => leg.geometry.map(([lon, lat]) => [lat, lon] as [number, number]))
      : [planFrom, planTo].filter((p): p is PlannerPlace => p !== null).map((p) => [p.lat, p.lon]);
    if (points.length < 2) return;
    const lats = points.map((p) => p[0]);
    const lons = points.map((p) => p[1]);
    flyTo({
      bounds: [
        [Math.min(...lats), Math.min(...lons)],
        [Math.max(...lats), Math.max(...lons)],
      ],
    });
  }, [plannerOpen, journey, planFrom, planTo, flyTo]);

  const setPlannerPlace = useCallback((field: PlannerField, place: PlannerPlace | null) => {
    (field === "from" ? setPlanFrom : setPlanTo)(place);
    setPicking(null);
  }, []);

  const openPlanner = useCallback(
    (field?: PlannerField, place?: PlannerPlace) => {
      setPlannerOpen(true);
      setSelection(null);
      setLayersOpen(false); // free the map so the journey is visible
      if (field && place) setPlannerPlace(field, place);
    },
    [setPlannerPlace],
  );
  const closePlanner = () => {
    setPlannerOpen(false);
    setPicking(null);
  };

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

  // While planning, clicking a stop fills A (or B) instead of opening the stop.
  const clickStopOnMap = (id: string) => {
    if (!plannerOpen) return selectStop(id);
    lastStopClick.current = Date.now();
    const field: PlannerField = picking ?? (planFrom ? "to" : "from");
    fetchJson<StopDetail>(`/api/stops/${encodeURIComponent(id)}`)
      .then((d) => setPlannerPlace(field, { name: d.name, lat: d.latitude, lon: d.longitude }))
      .catch(() => {});
  };
  const clickMap = (lat: number, lon: number) => {
    // a click on a stop also reaches the map: the stop handler already took care of it
    if (!plannerOpen || !picking || Date.now() - lastStopClick.current < 300) return;
    setPlannerPlace(picking, { name: "Point on the map", lat, lon });
  };

  const pickSearchStop = (result: StopSearchResult) => {
    setPlannerOpen(false);
    selectStop(result.stop_id);
    flyTo({ center: [result.latitude, result.longitude], zoom: 17 });
  };
  const pickSearchRoute = (result: RouteSummary) => {
    setPlannerOpen(false);
    selectRoute(result.route_id);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || aboutOpen) return;
      setPicking(null);
      setSelection(null);
    };
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
        plannerOpen={plannerOpen}
        onTogglePlanner={() => (plannerOpen ? closePlanner() : openPlanner())}
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
            onSelectStop={clickStopOnMap}
            onSelectRoute={plannerOpen ? () => {} : selectRouteOnMap}
            planner={plannerOpen ? { from: planFrom, to: planTo, journey } : null}
            picking={plannerOpen && picking !== null}
            onMapClick={clickMap}
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

        {plannerOpen && (
          <PlannerPanel
            from={planFrom}
            to={planTo}
            when={planWhen}
            picking={picking}
            plan={plan}
            selected={journeyIndex}
            onChange={setPlannerPlace}
            onSwap={() => {
              setPlanFrom(planTo);
              setPlanTo(planFrom);
            }}
            onWhenChange={setPlanWhen}
            onPick={setPicking}
            onSelectJourney={setJourneyIndex}
            onClose={closePlanner}
          />
        )}
        {!plannerOpen && selection?.kind === "stop" && (
          <StopPanel
            stopId={selection.id}
            stop={stop}
            onClose={() => setSelection(null)}
            onSelectStop={selectStopAndFly}
            onSelectRoute={selectRoute}
            onPlanFrom={(place) => openPlanner("from", place)}
            onPlanTo={(place) => openPlanner("to", place)}
          />
        )}
        {!plannerOpen && selection?.kind === "route" && (
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
