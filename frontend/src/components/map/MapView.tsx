import L from "leaflet";
import { useEffect, useMemo } from "react";
import {
  MapContainer,
  Pane,
  ScaleControl,
  TileLayer,
  useMap,
  useMapEvents,
  ZoomControl,
} from "react-leaflet";
import type { RouteDetail, StopDetail, UrbanLayerInfo } from "../../api/types";
import type { LayerState } from "../../config/layers";
import { BASE_MAPS, BUDAPEST_CENTER, DEFAULT_ZOOM, MAX_BOUNDS, MIN_ZOOM } from "../../config/map";
import type { FlyTarget, Viewport } from "../../state";
import { RoutesLayer } from "./RoutesLayer";
import { SelectedRouteLayer, SelectedStopMarker } from "./SelectionLayers";
import { StopsLayer } from "./StopsLayer";
import { UrbanLayer } from "./UrbanLayer";
import { VehiclesLayer } from "./VehiclesLayer";

interface Props {
  layers: LayerState;
  urbanLayers: UrbanLayerInfo[];
  realtimeEnabled: boolean;
  viewport: Viewport | null;
  onViewportChange: (viewport: Viewport) => void;
  selectedStop: StopDetail | null;
  selectedRoute: RouteDetail | null;
  fitSelectedRoute: boolean;
  flyTarget: FlyTarget | null;
  onSelectStop: (stopId: string) => void;
  onSelectRoute: (routeId: string) => void;
}

export function MapView(props: Props) {
  const { layers } = props;
  // One canvas renderer per map, with a click tolerance so thin route lines are easy to hit.
  const renderer = useMemo(() => L.canvas({ tolerance: 5 }), []);
  const baseMap = layers.baseMap === "none" ? null : BASE_MAPS[layers.baseMap];

  return (
    <MapContainer
      center={BUDAPEST_CENTER}
      zoom={DEFAULT_ZOOM}
      minZoom={MIN_ZOOM}
      maxBounds={MAX_BOUNDS}
      maxBoundsViscosity={0.8}
      zoomControl={false}
      preferCanvas
      renderer={renderer}
      className="map"
    >
      {baseMap && (
        <TileLayer
          key={layers.baseMap}
          url={baseMap.url}
          attribution={baseMap.attribution}
          maxZoom={baseMap.maxZoom}
          className={baseMap.className}
        />
      )}
      <ZoomControl position="bottomright" />
      <ScaleControl position="bottomleft" imperial={false} />
      <MapEvents onViewportChange={props.onViewportChange} flyTarget={props.flyTarget} />

      {/* Routes live in the default overlay pane; panes below stack above it. */}
      <RoutesLayer modes={layers.routeModes} onSelect={props.onSelectRoute} />

      <Pane name="stops" style={{ zIndex: 450 }}>
        <StopsLayer
          enabledModes={layers.stopModes}
          viewport={props.viewport}
          onSelect={props.onSelectStop}
        />
      </Pane>

      <Pane name="urban" style={{ zIndex: 455 }}>
        {props.urbanLayers
          .filter((info) => layers.urban.includes(info.id))
          .map((info) => (
            <UrbanLayer key={info.id} info={info} />
          ))}
      </Pane>

      {props.realtimeEnabled && layers.vehicles && (
        <Pane name="vehicles" style={{ zIndex: 458 }}>
          <VehiclesLayer onSelectRoute={props.onSelectRoute} onSelectStop={props.onSelectStop} />
        </Pane>
      )}

      <Pane name="selection" style={{ zIndex: 460 }}>
        {props.selectedRoute && (
          <SelectedRouteLayer
            route={props.selectedRoute}
            onSelectStop={props.onSelectStop}
            fitOnLoad={props.fitSelectedRoute}
          />
        )}
        {props.selectedStop && <SelectedStopMarker stop={props.selectedStop} />}
      </Pane>
    </MapContainer>
  );
}

function toViewport(map: L.Map): Viewport {
  const b = map.getBounds();
  return { bbox: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()], zoom: map.getZoom() };
}

/** Reports the visible area, performs fly-to requests and reacts to container resizes. */
function MapEvents({
  onViewportChange,
  flyTarget,
}: {
  onViewportChange: (viewport: Viewport) => void;
  flyTarget: FlyTarget | null;
}) {
  const map = useMapEvents({
    moveend: () => onViewportChange(toViewport(map)),
  });

  useEffect(() => {
    onViewportChange(toViewport(map));
  }, [map, onViewportChange]);

  useEffect(() => {
    if (!flyTarget) return;
    const zoom = flyTarget.zoom ?? map.getZoom();
    if (flyTarget.animate === false) {
      if (flyTarget.bounds) map.fitBounds(flyTarget.bounds, { padding: [40, 40] });
      else if (flyTarget.center) map.setView(flyTarget.center, zoom);
    } else if (flyTarget.bounds) {
      map.flyToBounds(flyTarget.bounds, { padding: [40, 40], duration: 0.8 });
    } else if (flyTarget.center) {
      map.flyTo(flyTarget.center, zoom, { duration: 0.8 });
    }
  }, [flyTarget, map]);

  return <ResizeWatcher />;
}

/** Leaflet must be told when its container changes size (e.g. the side panel opens). */
function ResizeWatcher() {
  const map = useMap();
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return null;
}
