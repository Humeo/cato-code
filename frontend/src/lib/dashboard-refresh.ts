export const DASHBOARD_REFRESH_INTERVAL_MS = 15_000;

export interface DashboardSnapshot {
  hasInitialData: boolean;
  lastLoadedAt: number;
  now?: number;
}

export function shouldRefreshDashboardOnMount(snapshot: DashboardSnapshot): boolean {
  if (!snapshot.hasInitialData) {
    return true;
  }
  return isDashboardDataStale(snapshot);
}

export function isDashboardDataStale(snapshot: DashboardSnapshot): boolean {
  const now = snapshot.now ?? Date.now();
  return now - snapshot.lastLoadedAt >= DASHBOARD_REFRESH_INTERVAL_MS;
}
