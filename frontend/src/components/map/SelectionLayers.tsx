import L from "leaflet";
import { useEffect } from "react";
import { CircleMarker, GeoJSON, Tooltip, useMap } from "react-leaflet";
import type { RouteDetail, StopDetail } from "../../api/types";
import { hexColor, MODES } from "../../config/transportModes";

/** Highlight ring around the selected stop. */
export function SelectedStopMarker({ stop }: { stop: StopDetail }) {
  return (
    <CircleMarker
      center={[stop.latitude, stop.longitude]}
      radius={12}
      pathOptions={{ color: "#0f172a", weight: 3, fillColor: "#22d3ee", fillOpacity: 0.35 }}
      interactive={false}
    />
  );
}

interface RouteProps {
  route: RouteDetail;
  onSelectStop: (stopId: string) => void;
  fitOnLoad: boolean;
}

/** The selected route drawn on top of everything, with its stops, zooming to fit it. */
export function SelectedRouteLayer({ route, onSelectStop, fitOnLoad }: RouteProps) {
  const map = useMap();
  const color = hexColor(route.color, MODES[route.mode].color);

  useEffect(() => {
    if (!fitOnLoad || !route.geometry) return;
    const bounds = L.geoJSON(route.geometry).getBounds();
    if (bounds.isValid()) map.flyToBounds(bounds, { padding: [40, 40], duration: 0.8 });
  }, [route.route_id, route.geometry, fitOnLoad, map]);

  const stops = new Map(
    route.directions.flatMap((d) => d.stops).map((s) => [s.stop_id, s] as const),
  );

  return (
    <>
      {route.geometry && (
        <>
          <GeoJSON
            key={`casing-${route.route_id}`}
            data={route.geometry}
            style={{ color: "#0f172a", weight: 10, opacity: 0.35 }}
            interactive={false}
          />
          <GeoJSON
            key={`line-${route.route_id}`}
            data={route.geometry}
            style={{ color, weight: 6, opacity: 1 }}
            interactive={false}
          />
        </>
      )}
      {[...stops.values()].map((stop) => (
        <CircleMarker
          key={stop.stop_id}
          center={[stop.latitude, stop.longitude]}
          radius={5}
          pathOptions={{ color, weight: 3, fillColor: "#ffffff", fillOpacity: 1 }}
          eventHandlers={{ click: () => onSelectStop(stop.stop_id) }}
        >
          <Tooltip direction="top">{stop.name}</Tooltip>
        </CircleMarker>
      ))}
    </>
  );
}
