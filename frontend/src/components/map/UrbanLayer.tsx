import type { FeatureCollection, Point } from "geojson";
import { CircleMarker, Popup } from "react-leaflet";
import type { UrbanFeatureProps, UrbanLayerInfo } from "../../api/types";
import { URBAN_LAYER_STYLES } from "../../config/layers";
import { useApi } from "../../hooks/useApi";

const TAG_LABELS: Record<string, string> = {
  operator: "Operator",
  network: "Network",
  capacity: "Capacity",
  "socket:type2": "Type 2 sockets",
  "socket:type2_combo": "CCS sockets",
  "socket:chademo": "CHAdeMO sockets",
  fee: "Fee",
  opening_hours: "Opening hours",
  access: "Access",
  bicycle_rental: "Type",
  parking: "Parking type",
};

/** One static OpenStreetMap layer (EV chargers, bike sharing, P+R). */
export function UrbanLayer({ info }: { info: UrbanLayerInfo }) {
  const { data } = useApi<FeatureCollection<Point, UrbanFeatureProps>>(`/api/layers/${info.id}`);
  const style = URBAN_LAYER_STYLES[info.id] ?? { color: "#64748b", symbol: "•" };
  if (!data) return null;

  return (
    <>
      {data.features.map((feature) => {
        const [lon, lat] = feature.geometry.coordinates;
        const props = feature.properties;
        return (
          <CircleMarker
            key={String(feature.id)}
            center={[lat, lon]}
            radius={6}
            pathOptions={{ color: "#ffffff", weight: 2, fillColor: style.color, fillOpacity: 0.9 }}
          >
            <Popup pane="popupPane">
              <div className="poi-popup">
                <div className="poi-title">
                  <span className="poi-symbol" style={{ background: style.color }}>
                    {style.symbol}
                  </span>
                  <strong>{props.name ?? info.title}</strong>
                </div>
                <dl>
                  {Object.entries(props.details).map(([key, value]) => (
                    <div key={key}>
                      <dt>{TAG_LABELS[key] ?? key}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
                <p className="poi-source">
                  Static OpenStreetMap data ·{" "}
                  <a href={props.osm_url} target="_blank" rel="noreferrer">
                    view on OSM
                  </a>
                </p>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}
