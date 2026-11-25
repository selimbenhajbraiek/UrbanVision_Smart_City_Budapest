import type { PlanResponse } from "../../api/types";
import type { ApiState } from "../../hooks/useApi";
import type { PlannerField, PlannerPlace } from "../../state";
import { DataStatusBadge } from "../common/Badges";
import { Icon } from "../common/Icon";
import { PanelMessage, SidePanel } from "../panels/SidePanel";
import { JourneyList } from "./JourneyList";
import { JourneySteps } from "./JourneySteps";
import { PlaceInput } from "./PlaceInput";

export interface PlannerTime {
  date: string; // YYYY-MM-DD
  time: string; // HH:MM
}

interface Props {
  from: PlannerPlace | null;
  to: PlannerPlace | null;
  when: PlannerTime | null; // null = leave now
  picking: PlannerField | null;
  plan: ApiState<PlanResponse>;
  selected: number;
  onChange: (field: PlannerField, place: PlannerPlace | null) => void;
  onSwap: () => void;
  onWhenChange: (when: PlannerTime | null) => void;
  onPick: (field: PlannerField | null) => void;
  onSelectJourney: (index: number) => void;
  onClose: () => void;
}

function nowParts(): PlannerTime {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Budapest",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date());
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return { date: `${get("year")}-${get("month")}-${get("day")}`, time: `${get("hour")}:${get("minute")}` };
}

export function PlannerPanel(props: Props) {
  const { from, to, when, picking, plan, selected } = props;
  const result = plan.data;
  const journey = result?.journeys[selected] ?? null;

  return (
    <SidePanel
      title="Plan a trip"
      subtitle={<span className="muted">From A to B by public transport</span>}
      onClose={props.onClose}
    >
      <section className="panel-section planner-form">
        <div className="planner-places">
          <div className="grow">
            <PlaceInput
              label="From"
              marker="A"
              place={from}
              picking={picking === "from"}
              onChange={(p) => props.onChange("from", p)}
              onPickOnMap={() => props.onPick(picking === "from" ? null : "from")}
            />
            <PlaceInput
              label="To"
              marker="B"
              place={to}
              picking={picking === "to"}
              onChange={(p) => props.onChange("to", p)}
              onPickOnMap={() => props.onPick(picking === "to" ? null : "to")}
            />
          </div>
          <button
            type="button"
            className="icon-button swap-button"
            onClick={props.onSwap}
            aria-label="Swap start and destination"
            title="Swap"
          >
            <Icon name="swap" />
          </button>
        </div>

        <div className="planner-when">
          <label className="check">
            <input type="radio" checked={when === null} onChange={() => props.onWhenChange(null)} />
            Leave now
          </label>
          <label className="check">
            <input
              type="radio"
              checked={when !== null}
              onChange={() => props.onWhenChange(nowParts())}
            />
            Leave at
          </label>
          {when && (
            <span className="planner-when-inputs">
              <input
                type="date"
                aria-label="Date"
                value={when.date}
                onChange={(e) => e.target.value && props.onWhenChange({ ...when, date: e.target.value })}
              />
              <input
                type="time"
                aria-label="Time"
                value={when.time}
                onChange={(e) => e.target.value && props.onWhenChange({ ...when, time: e.target.value })}
              />
            </span>
          )}
        </div>

        {picking && (
          <PanelMessage>
            Click on the map (or on a stop) to choose {picking === "from" ? "the start (A)" : "the destination (B)"}.
          </PanelMessage>
        )}
        {!picking && (!from || !to) && (
          <p className="muted planner-hint">
            Search a stop, use <Icon name="pin" size={13} /> to click a point on the map, or open a stop and
            choose “From here” / “To here”.
          </p>
        )}
      </section>

      {from && to && (
        <section className="panel-section">
          <div className="section-heading">
            <h3>Journeys</h3>
            <DataStatusBadge status="scheduled" />
            {plan.loading && <span className="muted">Searching…</span>}
          </div>
          {plan.error && <PanelMessage tone="error">{plan.error}</PanelMessage>}
          {result?.notice && <PanelMessage>{result.notice}</PanelMessage>}
          {result && result.journeys.length > 0 && (
            <JourneyList journeys={result.journeys} selected={selected} onSelect={props.onSelectJourney} />
          )}
        </section>
      )}

      {result && journey && (
        <section className="panel-section">
          <h3>Step by step</h3>
          <JourneySteps journey={journey} destination={result.destination.name} />
          <p className="muted planner-note">
            Times come from the official BKK timetable; live delays are not included.
          </p>
        </section>
      )}
    </SidePanel>
  );
}
