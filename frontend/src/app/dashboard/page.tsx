import { LiveDashboard } from "@/components/LiveDashboard";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <LiveDashboard
        initialStats={null}
        initialActivities={[]}
        initialRepos={[]}
      />
    </div>
  );
}
