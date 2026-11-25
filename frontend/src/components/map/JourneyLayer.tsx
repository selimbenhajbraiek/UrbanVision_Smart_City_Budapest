import L from "leaflet";
import { Fragment, useMemo } from "react";
import { CircleMarker, Marker, Polyline, Tooltip } from "react-leaflet";
import type { Journey } from "../../api/types";
import { hexColor, MODES } from "../../config/transportModes";
import type { PlannerPlace } from "../../state";

function letterIcon(letter: "A" | "B") {
  return L.divIcon({
    className: "",
    html: `<span class="place-marker place-marker-${letter} map-pin">${letter}</span>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

interface Props {
  from: PlannerPlace | null;
  to: PlannerPlace | null;
  journey: Journey | null;
}

/** The selected journey: coloured vehicle legs, dashed walks, boarding points and A/B pins. */
export function JourneyLayer({ from, to, journey }: Props) {
  const icons = useMemo(() => ({ A: letterIcon("A"), B: letterIcon("B") }), []);
  return (
    <>
      {journey?.legs.map((leg, i) => {
        const points = leg.geometry.map(([lon, lat]) => [lat, lon] as [number, number]);
        if (leg.kind === "walk") {
          return (
            <Polyline
              key={i}
              positions={points}
              pathOptions={{ color: "#334155", weight: 4, dashArray: "2 8", lineCap: "round" }}
            />
          );
        }
        const color = hexColor(leg.route!.color, MODES[leg.route!.mode].color);
        // dark outline + white gap under the line colour: stands out even on top of a
        // network drawn in the same colour (e.g. a yellow tram among yellow tram lines)
        return (
          <Fragment key={i}>
            <Polyline positions={points} pathOptions={{ color: "#0f172a", weight: 13, opacity: 0.9 }} />
            <Polyline positions={points} pathOptions={{ color: "#ffffff", weight: 9 }} />
            <Polyline positions={points} pathOptions={{ color, weight: 6 }} />
          </Fragment>
        );
      })}
      {journey?.legs
        .filter((leg) => leg.kind === "transit")
        .flatMap((leg, i) => [
          <CircleMarker
            key={`board-${i}`}
            center={[leg.start.latitude, leg.start.longitude]}
            radius={6}
            pathOptions={{ color: "#0f172a", weight: 2, fillColor: "#fff", fillOpacity: 1 }}
          >
            <Tooltip direction="top">
              {leg.route!.short_name} · {leg.start.name}
            </Tooltip>
          </CircleMarker>,
          <CircleMarker
            key={`alight-${i}`}
            center={[leg.end.latitude, leg.end.longitude]}
            radius={6}
            pathOptions={{ color: "#0f172a", weight: 2, fillColor: "#fff", fillOpacity: 1 }}
          >
            <Tooltip direction="top">{leg.end.name}</Tooltip>
          </CircleMarker>,
        ])}
      {from && <Marker position={[from.lat, from.lon]} icon={icons.A} title={`A: ${from.name}`} />}
      {to && <Marker position={[to.lat, to.lon]} icon={icons.B} title={`B: ${to.name}`} />}
    </>
  );
}
