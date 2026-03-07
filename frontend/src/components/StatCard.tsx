interface StatCardProps {
  label: string;
  value: string | number;
  accent?: string;
}

export function StatCard({ label, value, accent }: StatCardProps) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ?? "text-white"}`}>{value}</p>
    </div>
  );
}
