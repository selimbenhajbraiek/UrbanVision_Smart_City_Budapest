import type { AdminStats } from "../../api/types";
import { formatNumber } from "../../utils/format";

export function AdminStatsCards({ stats }: { stats: AdminStats }) {
  const cards: { label: string; value: number; hint?: string }[] = [
    { label: "Users", value: stats.users.total, hint: `${stats.users.active} active` },
    { label: "Admins", value: stats.users.admins },
    { label: "New this week", value: stats.users.new_last_7_days },
    { label: "Logins this week", value: stats.users.logins_last_7_days },
    { label: "Stops", value: stats.stops },
    { label: "Lines", value: stats.routes },
    { label: "Trips today", value: stats.trips_today },
    { label: "Urban features", value: stats.urban_features, hint: "EV, bikes, P+R" },
  ];
  return (
    <div className="admin-cards">
      {cards.map((card) => (
        <div key={card.label} className="admin-card">
          <span className="admin-card-label">{card.label}</span>
          <strong className="admin-card-value">{formatNumber(card.value)}</strong>
          {card.hint && <span className="muted">{card.hint}</span>}
        </div>
      ))}
    </div>
  );
}
