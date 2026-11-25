import { Link } from "react-router-dom";
import type { RouteSummary, StopSearchResult } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { Icon } from "../common/Icon";
import { SearchBox } from "./SearchBox";

/** Log in, or (when logged in) the user's e-mail, an Admin link for admins, and Log out. */
function AccountButtons() {
  const { user, checking, logout } = useAuth();
  if (checking) return null;
  if (!user) {
    return (
      <Link to="/login" className="header-button">
        <Icon name="user" /> <span className="label">Log in</span>
      </Link>
    );
  }
  return (
    <>
      {user.role === "admin" && (
        <Link to="/admin" className="header-button">
          <Icon name="shield" /> <span className="label">Admin</span>
        </Link>
      )}
      <button type="button" className="header-button" onClick={logout} title={`Log out ${user.email}`}>
        <Icon name="logout" /> <span className="label">Log out</span>
      </button>
    </>
  );
}

interface Props {
  layersOpen: boolean;
  activeLayers: number;
  onToggleLayers: () => void;
  plannerOpen: boolean;
  onTogglePlanner: () => void;
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
          className={`header-button ${props.plannerOpen ? "active" : ""}`}
          onClick={props.onTogglePlanner}
          aria-pressed={props.plannerOpen}
        >
          <Icon name="route" /> <span className="label">Plan trip</span>
        </button>
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
        <AccountButtons />
      </nav>
    </header>
  );
}
