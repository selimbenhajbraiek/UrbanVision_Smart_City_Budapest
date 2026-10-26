import type { ReactNode } from "react";
import { Icon } from "../common/Icon";

interface Props {
  title: string;
  subtitle?: ReactNode;
  onClose: () => void;
  children: ReactNode;
}

export function SidePanel({ title, subtitle, onClose, children }: Props) {
  return (
    <aside className="side-panel" aria-label={title}>
      <header className="side-panel-header">
        <div>
          <h2>{title}</h2>
          {subtitle && <div className="side-panel-subtitle">{subtitle}</div>}
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close panel">
          <Icon name="close" />
        </button>
      </header>
      <div className="side-panel-body">{children}</div>
    </aside>
  );
}

export function PanelMessage({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "error" }) {
  return <div className={`panel-message panel-message-${tone}`}>{children}</div>;
}
