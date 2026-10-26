import type L from "leaflet";
import type { Feature, FeatureCollection, MultiLineString } from "geojson";
import { useMemo, useRef } from "react";
import { GeoJSON } from "react-leaflet";
import { query } from "../../api/client";
import type { Mode, RouteFeatureProps } from "../../api/types";
import { BKK_ATTRIBUTION } from "../../config/map";
import { hexColor, MODES } from "../../config/transportModes";
import { useApi } from "../../hooks/useApi";
import { escapeHtml } from "./StopsLayer";

interface Props {
  modes: Mode[];
  onSelect: (routeId: string) => void;
}

export function RoutesLayer({ modes, onSelect }: Props) {
  const path = modes.length > 0 ? `/api/routes/geometry${query({ mode: modes.join(",") })}` : null;
  const { data } = useApi<FeatureCollection<MultiLineString, RouteFeatureProps>>(path);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  const options = useMemo(
    () => ({
      style: (feature?: Feature) => {
        const props = feature!.properties as RouteFeatureProps;
        return {
          color: hexColor(props.color, MODES[props.mode].color),
          weight: MODES[props.mode].lineWeight,
          opacity: 0.85,
          lineCap: "round" as const,
        };
      },
      onEachFeature: (feature: Feature<MultiLineString, RouteFeatureProps>, layer: L.Layer) => {
        const { short_name, description, mode, route_id } = feature.properties;
        layer.bindTooltip(
          `<strong>${MODES[mode].label} ${escapeHtml(short_name ?? "")}</strong>` +
            (description ? `<br/>${escapeHtml(description)}` : ""),
          { sticky: true },
        );
        layer.on("click", () => onSelectRef.current(route_id));
      },
    }),
    [],
  );

  if (!data || !path) return null;
  return (
    <GeoJSON
      key={path}
      data={data}
      {...options}
      attribution={BKK_ATTRIBUTION}
    />
  );
}
