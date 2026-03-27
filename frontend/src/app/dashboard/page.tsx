import { cookies } from "next/headers";

import { LiveDashboard } from "@/components/LiveDashboard";
import { getDashboard } from "@/lib/api";

export default async function DashboardPage() {
  const cookieHeader = (await cookies()).toString();
  const requestInit = cookieHeader ? { headers: { cookie: cookieHeader } } : undefined;
  const initialDashboard = await getDashboard(requestInit);

  return (
    <div className="space-y-6">
      <LiveDashboard
        initialStats={initialDashboard?.stats ?? null}
        initialActivities={initialDashboard?.activities ?? []}
        initialRepos={initialDashboard?.repos ?? []}
      />
    </div>
  );
}
