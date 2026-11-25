import type { Journey } from "../../api/types";
import { formatClock } from "../../utils/format";
import { RouteBadge } from "../common/Badges";
import { Icon } from "../common/Icon";

interface Props {
  journeys: Journey[];
  selected: number;
  onSelect: (index: number) => void;
}

/** One summary line per option: times, duration, changes, and the lines used. */
export function JourneyList({ journeys, selected, onSelect }: Props) {
  const fastest = Math.min(...journeys.map((j) => new Date(j.arrival).getTime()));
  return (
    <ul className="journey-list">
      {journeys.map((journey, index) => {
        const transit = journey.legs.filter((leg) => leg.kind === "transit");
        const isFastest = new Date(journey.arrival).getTime() === fastest;
        return (
          <li key={index}>
            <button
              type="button"
              className={`journey-option ${index === selected ? "selected" : ""}`}
              aria-pressed={index === selected}
              onClick={() => onSelect(index)}
            >
              <div className="journey-times">
                <strong>
                  {formatClock(journey.departure)} → {formatClock(journey.arrival)}
                </strong>
                <span className="journey-duration">{journey.duration_minutes} min</span>
              </div>
              <div className="journey-lines">
                {transit.length === 0 ? (
                  <span className="walk-chip">
                    <Icon name="walk" size={14} /> Walk only
                  </span>
                ) : (
                  transit.map((leg, i) => (
                    <span key={i} className="journey-line">
                      {i > 0 && <span className="muted">›</span>}
                      <RouteBadge
                        shortName={leg.route!.short_name}
                        color={leg.route!.color}
                        textColor={leg.route!.text_color}
                        mode={leg.route!.mode}
                      />
                    </span>
                  ))
                )}
              </div>
              <div className="journey-meta muted">
                {transit.length > 0 &&
                  (journey.transfers === 0
                    ? "No change"
                    : `${journey.transfers} change${journey.transfers > 1 ? "s" : ""}`)}
                {transit.length > 0 && " · "}
                {journey.walking_minutes} min walk
                {isFastest && journeys.length > 1 && <span className="fastest-tag">Fastest</span>}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
