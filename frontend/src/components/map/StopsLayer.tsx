import L from "leaflet";
import type { Feature, FeatureCollection, Point } from "geojson";
import { useMemo, useRef } from "react";
import { GeoJSON } from "react-leaflet";
import { query } from "../../api/client";
import type { Mode, StopFeatureProps } from "../../api/types";
import { BKK_ATTRIBUTION } from "../../config/map";
import { MODES, primaryMode, visibleStopModes } from "../../config/transportModes";
import { useApi } from "../../hooks/useApi";
import type { Viewport } from "../../state";

interface Props {
  enabledModes: Mode[];
  viewport: Viewport | null;
  onSelect: (stopId: string) => void;
}

/** Enlarge the requested area a little so small pans don't trigger a new request. */
function paddedBbox([minLon, minLat, maxLon, maxLat]: Viewport["bbox"]): string {
  const padLon = (maxLon - minLon) * 0.15;
  const padLat = (maxLat - minLat) * 0.15;
  return [minLon - padLon, minLat - padLat, maxLon + padLon, maxLat + padLat]
    .map((v) => v.toFixed(3))
    .join(",");
}

export function StopsLayer({ enabledModes, viewport, onSelect }: Props) {
  const modes = viewport ? visibleStopModes(enabledModes, viewport.zoom) : [];
  const path =
    viewport && modes.length > 0
      ? `/api/stops${query({ bbox: paddedBbox(viewport.bbox), mode: modes.join(","), limit: 4000 })}`
      : null;
  const { data } = useApi<FeatureCollection<Point, StopFeatureProps>>(path);

  // Leaflet handlers are created once per GeoJSON layer, so read the latest callback via a ref.
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  const radius = viewport && viewport.zoom >= 16 ? 6 : 4.5;
  const options = useMemo(
    () => ({
      pointToLayer: (feature: Feature<Point, StopFeatureProps>, latlng: L.LatLng) => {
        const mode = primaryMode(feature.properties.modes);
        const isRail = mode === "metro" || mode === "hev";
        return L.circleMarker(latlng, {
          radius: isRail ? radius + 1.5 : radius,
          color: "#ffffff",
          weight: 1.5,
          fillColor: MODES[mode].color,
          fillOpacity: 0.95,
        });
      },
      onEachFeature: (feature: Feature<Point, StopFeatureProps>, layer: L.Layer) => {
        const { name, modes: stopModes, stop_id } = feature.properties;
        layer.bindTooltip(
          `<strong>${escapeHtml(name)}</strong><br/>${stopModes.map((m) => MODES[m].label).join(" · ")}`,
          { direction: "top", offset: [0, -4] },
        );
        layer.on("click", () => onSelectRef.current(stop_id));
      },
    }),
    [radius],
  );

  if (!data || !path) return null;
  // `key` forces a fresh Leaflet layer when the data changes (react-leaflet GeoJSON is immutable).
  return (
    <GeoJSON
      key={`${path}-${radius}-${data.features.length}`}
      data={data}
      {...options}
      attribution={BKK_ATTRIBUTION}
    />
  );
}

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}
