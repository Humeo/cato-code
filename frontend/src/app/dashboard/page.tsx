import { cookies } from "next/headers";

import { LiveDashboard } from "@/components/LiveDashboard";
import { getActivities, getRepos, getStats } from "@/lib/api";

export default async function DashboardPage() {
  const cookieHeader = (await cookies()).toString();
  const requestInit = cookieHeader ? { headers: { cookie: cookieHeader } } : undefined;
  const [initialStats, initialActivities, initialRepos] = await Promise.all([
    getStats(requestInit),
    getActivities(requestInit),
    getRepos(requestInit),
  ]);

  return (
    <div className="space-y-6">
      <LiveDashboard
        initialStats={initialStats}
        initialActivities={initialActivities ?? []}
        initialRepos={initialRepos ?? []}
      />
    </div>
  );
}
