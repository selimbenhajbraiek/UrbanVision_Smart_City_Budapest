import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AdminDataStatus, User } from "../../api/types";
import { DataStatusCard } from "./DataStatusCard";
import { UsersTable } from "./UsersTable";

const users: User[] = [
  {
    id: 1,
    email: "admin@example.com",
    role: "admin",
    is_active: true,
    created_at: "2026-11-01T10:00:00Z",
    last_login_at: "2026-11-25T10:00:00Z",
  },
  {
    id: 2,
    email: "user@example.com",
    role: "user",
    is_active: true,
    created_at: "2026-11-20T10:00:00Z",
    last_login_at: null,
  },
];

const status: AdminDataStatus = {
  feed: {
    publisher_name: "BKK",
    feed_version: "1",
    valid_from: "2026-11-20",
    valid_to: "2026-12-28",
    imported_at: "2026-11-25T11:00:00Z",
    covers_today: true,
  },
  days_until_expiry: 33,
  layers: [{ id: "ev_charging", title: "EV charging stations", feature_count: 561, imported_at: null }],
  realtime_enabled: false,
};

describe("UsersTable", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("lists users and hides actions on your own row", () => {
    render(<UsersTable users={users} currentUserId={1} onChanged={() => {}} />);
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    expect(screen.getByText("(you)")).toBeInTheDocument();
    // only the other user's row has buttons
    expect(screen.getAllByRole("button", { name: "Make admin" })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Make user" })).not.toBeInTheDocument();
  });

  it("promotes a user and refreshes the list", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ ...users[1], role: "admin" })));
    const onChanged = vi.fn();
    render(<UsersTable users={users} currentUserId={1} onChanged={onChanged} />);
    await userEvent.click(screen.getByRole("button", { name: "Make admin" }));
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/admin/users/2");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ role: "admin" });
    expect(onChanged).toHaveBeenCalled();
  });

  it("asks for confirmation before deleting", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    render(<UsersTable users={users} currentUserId={1} onChanged={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(fetchMock).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
    expect(fetchMock.mock.calls[0][1].method).toBe("DELETE");
  });
});

describe("DataStatusCard", () => {
  it("is green when the timetable is valid", () => {
    render(<DataStatusCard status={status} />);
    expect(screen.getByText("Timetable is up to date.")).toBeInTheDocument();
    expect(screen.getByText(/Not imported/)).toBeInTheDocument();
  });

  it("warns when the timetable ends soon or has expired", () => {
    const { rerender } = render(<DataStatusCard status={{ ...status, days_until_expiry: 3 }} />);
    expect(screen.getByText(/ends in 3 days/)).toBeInTheDocument();
    rerender(
      <DataStatusCard
        status={{ ...status, days_until_expiry: -2, feed: { ...status.feed!, covers_today: false } }}
      />,
    );
    expect(screen.getByText(/has expired/)).toBeInTheDocument();
  });
});
