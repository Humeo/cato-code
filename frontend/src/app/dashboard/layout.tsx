import { getMe } from "@/lib/api";
import { redirect } from "next/navigation";
import { UserNav } from "@/components/UserNav";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getMe();

  if (!user) {
    redirect("/");
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <span className="text-3xl">🐱</span>
        <div>
          <h1 className="text-2xl font-bold text-white">CatoCode</h1>
          <p className="text-gray-400 text-sm">Autonomous Code Maintenance Agent</p>
        </div>
        <div className="ml-auto flex items-center gap-4">
          <div className="w-3 h-3 rounded-full bg-green-400 animate-pulse" />
          <UserNav user={user} />
        </div>
      </div>

      {children}
    </div>
  );
}
