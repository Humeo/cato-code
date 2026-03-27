import { describe, expect, it } from "bun:test";

import {
  DASHBOARD_REFRESH_INTERVAL_MS,
  isDashboardDataStale,
  shouldRefreshDashboardOnMount,
} from "./dashboard-refresh";

describe("dashboard refresh policy", () => {
  it("refreshes immediately when there is no initial data", () => {
    expect(
      shouldRefreshDashboardOnMount({
        hasInitialData: false,
        lastLoadedAt: 0,
        now: 0,
      })
    ).toBe(true);
  });

  it("does not refresh immediately when SSR already provided fresh data", () => {
    expect(
      shouldRefreshDashboardOnMount({
        hasInitialData: true,
        lastLoadedAt: 1_000,
        now: 1_000 + DASHBOARD_REFRESH_INTERVAL_MS - 1,
      })
    ).toBe(false);
  });

  it("marks data as stale after the refresh interval elapses", () => {
    expect(
      isDashboardDataStale({
        hasInitialData: true,
        lastLoadedAt: 1_000,
        now: 1_000 + DASHBOARD_REFRESH_INTERVAL_MS,
      })
    ).toBe(true);
  });
});
