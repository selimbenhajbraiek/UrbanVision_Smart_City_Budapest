import type { Journey, PlanLeg } from "../../api/types";
import { MODES } from "../../config/transportModes";
import { formatClock } from "../../utils/format";
import { RouteBadge } from "../common/Badges";
import { Icon } from "../common/Icon";

function WalkStep({ leg }: { leg: PlanLeg }) {
  return (
    <li className="step step-walk">
      <span className="step-time">{formatClock(leg.departure)}</span>
      <span className="step-icon" aria-hidden>
        <Icon name="walk" size={16} />
      </span>
      <div className="step-body">
        <strong>
          Walk {leg.duration_minutes} min
          <span className="muted"> · {leg.distance_m} m</span>
        </strong>
        <span className="muted">to {leg.end.name}</span>
      </div>
    </li>
  );
}

function TransitStep({ leg }: { leg: PlanLeg }) {
  const route = leg.route!;
  const stops = leg.stop_count ?? 0;
  return (
    <li className="step step-transit">
      <span className="step-time">{formatClock(leg.departure)}</span>
      <span className="step-icon" aria-hidden>
        <RouteBadge
          shortName={route.short_name}
          color={route.color}
          textColor={route.text_color}
          mode={route.mode}
        />
      </span>
      <div className="step-body">
        <strong>
          {MODES[route.mode].label} {route.short_name} <span className="muted">towards</span>{" "}
          {leg.headsign ?? leg.end.name}
        </strong>
        <span>
          Board at <b>{leg.start.name}</b>
        </span>
        <details className="step-stops">
          <summary>
            {stops} stop{stops === 1 ? "" : "s"} · {leg.duration_minutes} min
            {leg.wheelchair_accessible && (
              <span title="Accessible vehicle">
                {" "}
                · <Icon name="wheelchair" size={12} />
              </span>
            )}
          </summary>
          <ol>
            {leg.intermediate_stops.map((stop, i) => (
              <li key={`${stop.stop_id}-${i}`}>{stop.name}</li>
            ))}
          </ol>
        </details>
        <span>
          Get off at <b>{leg.end.name}</b> <span className="muted">({formatClock(leg.arrival)})</span>
        </span>
      </div>
    </li>
  );
}

/** "Walk 2 min → M2 towards Örs vezér tere, 6 stops → walk 1 min → arrive". */
export function JourneySteps({ journey, destination }: { journey: Journey; destination: string }) {
  return (
    <ol className="steps">
      {journey.legs.map((leg, i) =>
        leg.kind === "walk" ? <WalkStep key={i} leg={leg} /> : <TransitStep key={i} leg={leg} />,
      )}
      <li className="step step-arrive">
        <span className="step-time">{formatClock(journey.arrival)}</span>
        <span className="step-icon place-marker place-marker-B" aria-hidden>
          B
        </span>
        <div className="step-body">
          <strong>Arrive at {destination}</strong>
        </div>
      </li>
    </ol>
  );
}
