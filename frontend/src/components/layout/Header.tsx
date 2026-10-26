import type { RouteSummary, StopSearchResult } from "../../api/types";
import { Icon } from "../common/Icon";
import { SearchBox } from "./SearchBox";

interface Props {
  layersOpen: boolean;
  activeLayers: number;
  onToggleLayers: () => void;
  onOpenAbout: () => void;
  onResetView: () => void;
  onPickStop: (stop: StopSearchResult) => void;
  onPickRoute: (route: RouteSummary) => void;
}

export function Header(props: Props) {
  return (
    <header className="app-header">
      <div className="brand">
        <img src="/favicon.svg" alt="" width={28} height={28} />
        <div>
          <h1>UrbanVision</h1>
          <span>Budapest Smart City Map</span>
        </div>
      </div>
      <SearchBox onPickStop={props.onPickStop} onPickRoute={props.onPickRoute} />
      <nav className="header-actions">
        <button
          type="button"
          className={`header-button ${props.layersOpen ? "active" : ""}`}
          onClick={props.onToggleLayers}
          aria-pressed={props.layersOpen}
        >
          <Icon name="layers" /> <span className="label">Data layers</span>
          <span className="count">{props.activeLayers}</span>
        </button>
        <button type="button" className="header-button" onClick={props.onResetView} title="Reset view">
          <Icon name="home" /> <span className="label">Budapest</span>
        </button>
        <button type="button" className="header-button" onClick={props.onOpenAbout}>
          <Icon name="info" /> <span className="label">Data sources</span>
        </button>
      </nav>
    </header>
  );
}
