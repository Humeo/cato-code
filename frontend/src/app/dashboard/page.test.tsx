import { describe, expect, it, mock } from "bun:test";
import type { ReactNode } from "react";

const statsPayload = {
  repos: { total: 1, watched: 1 },
  activities: { by_status: { done: 1 }, by_kind: { setup: 1 }, total: 1 },
  cost_usd: 0.12,
  recent_activities: [],
};

const activitiesPayload = [{ id: "activity-1" }];
const reposPayload = [{ id: "repo-1" }];

const getStats = mock(async (_init?: RequestInit) => statsPayload);
const getActivities = mock(async (_init?: RequestInit) => activitiesPayload);
const getRepos = mock(async (_init?: RequestInit) => reposPayload);
const cookies = mock(async () => ({ toString: () => "session=session-1" }));

mock.module("next/headers", () => ({
  cookies,
}));

mock.module("@/lib/api", () => ({
  getStats,
  getActivities,
  getRepos,
}));

mock.module("@/components/LiveDashboard", () => ({
  LiveDashboard: (props: { initialStats: unknown; initialActivities: unknown; initialRepos: unknown }): ReactNode => ({
    type: "mock-live-dashboard",
    props,
  }),
}));

describe("DashboardPage", () => {
  it("hydrates LiveDashboard with server-fetched data", async () => {
    const mod = await import("./page");
    const page = await mod.default();
    const liveDashboard = page.props.children;

    expect(cookies).toHaveBeenCalled();
    expect(getStats).toHaveBeenCalledWith({ headers: { cookie: "session=session-1" } });
    expect(getActivities).toHaveBeenCalledWith({ headers: { cookie: "session=session-1" } });
    expect(getRepos).toHaveBeenCalledWith({ headers: { cookie: "session=session-1" } });
    expect(liveDashboard.props.initialStats).toEqual(statsPayload);
    expect(liveDashboard.props.initialActivities).toEqual(activitiesPayload);
    expect(liveDashboard.props.initialRepos).toEqual(reposPayload);
  });
});
