import type { Mode, RealtimeStatus, UrbanLayerInfo } from "../../api/types";
import { toggle, type LayerState, URBAN_LAYER_STYLES } from "../../config/layers";
import { BASE_MAPS, type BaseMapId } from "../../config/map";
import { MODES, TRANSIT_MODES } from "../../config/transportModes";
import { formatNumber } from "../../utils/format";
import { DataStatusBadge } from "../common/Badges";
import { Icon } from "../common/Icon";

interface Props {
  layers: LayerState;
  onChange: (layers: LayerState) => void;
  urbanLayers: UrbanLayerInfo[];
  realtime: RealtimeStatus | null;
  zoom: number | null;
  onClose: () => void;
}

export function LayerPanel({ layers, onChange, urbanLayers, realtime, zoom, onClose }: Props) {
  const set = (patch: Partial<LayerState>) => onChange({ ...layers, ...patch });

  return (
    <section className="layer-panel" aria-label="Data layers">
      <header>
        <h2>
          <Icon name="layers" /> Data layers
        </h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close layers">
          <Icon name="close" />
        </button>
      </header>

      <fieldset>
        <legend>Base map</legend>
        {(["muted", "osm", "none"] as BaseMapId[]).map((id) => (
          <label key={id} className="check">
            <input
              type="radio"
              name="basemap"
              checked={layers.baseMap === id}
              onChange={() => set({ baseMap: id })}
            />
            {id === "none" ? "None" : BASE_MAPS[id].label}
          </label>
        ))}
      </fieldset>

      <fieldset>
        <legend>
          Public transport stops <DataStatusBadge status="scheduled" />
        </legend>
        {TRANSIT_MODES.map((mode) => (
          <ModeCheckbox
            key={mode}
            mode={mode}
            checked={layers.stopModes.includes(mode)}
            onChange={() => set({ stopModes: toggle(layers.stopModes, mode) })}
            hint={zoom !== null && zoom < MODES[mode].minStopZoom ? `zoom ≥ ${MODES[mode].minStopZoom}` : undefined}
          />
        ))}
      </fieldset>

      <fieldset>
        <legend>Transport routes</legend>
        {TRANSIT_MODES.map((mode) => (
          <ModeCheckbox
            key={mode}
            mode={mode}
            checked={layers.routeModes.includes(mode)}
            onChange={() => set({ routeModes: toggle(layers.routeModes, mode) })}
          />
        ))}
      </fieldset>

      <fieldset>
        <legend>
          Environment <DataStatusBadge status="model" />
        </legend>
        <label className="check">
          <input type="checkbox" checked={layers.weather} onChange={() => set({ weather: !layers.weather })} />
          Weather (Open-Meteo)
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={layers.airQuality}
            onChange={() => set({ airQuality: !layers.airQuality })}
          />
          Air quality (CAMS)
        </label>
      </fieldset>

      <fieldset>
        <legend>
          Urban data <DataStatusBadge status="static" />
        </legend>
        {urbanLayers.map((info) => (
          <label key={info.id} className="check" title={info.description}>
            <input
              type="checkbox"
              checked={layers.urban.includes(info.id)}
              disabled={info.feature_count === 0}
              onChange={() => set({ urban: toggle(layers.urban, info.id) })}
            />
            <span className="swatch" style={{ background: URBAN_LAYER_STYLES[info.id]?.color }} />
            {info.title}
            <span className="muted">
              {info.feature_count > 0 ? formatNumber(info.feature_count) : "not imported"}
            </span>
          </label>
        ))}
      </fieldset>

      <fieldset>
        <legend>
          Real-time <DataStatusBadge status="realtime" />
        </legend>
        <label className="check" title={realtime?.message}>
          <input
            type="checkbox"
            checked={layers.vehicles && !!realtime?.enabled}
            disabled={!realtime?.enabled}
            onChange={() => set({ vehicles: !layers.vehicles })}
          />
          Live vehicle positions
        </label>
        {realtime && !realtime.enabled && <p className="footnote">{realtime.message}</p>}
      </fieldset>
    </section>
  );
}

function ModeCheckbox({
  mode,
  checked,
  onChange,
  hint,
}: {
  mode: Mode;
  checked: boolean;
  onChange: () => void;
  hint?: string;
}) {
  return (
    <label className="check">
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className="swatch" style={{ background: MODES[mode].color }} />
      {MODES[mode].label}
      {hint && checked && <span className="muted">{hint}</span>}
    </label>
  );
}
