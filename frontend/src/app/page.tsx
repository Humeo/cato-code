import { getMe } from "@/lib/api";
import { redirect } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default async function HomePage() {
  const user = await getMe();

  // If already authenticated, redirect to dashboard
  if (user) {
    redirect("/dashboard");
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-md w-full text-center space-y-8">
        {/* Logo + name */}
        <div>
          <span className="text-6xl">🐱</span>
          <h1 className="text-4xl font-bold text-white mt-4">CatoCode</h1>
          <p className="text-gray-400 mt-2">
            Autonomous AI-powered GitHub repository maintenance
          </p>
        </div>

        {/* Feature bullets */}
        <ul className="text-left text-sm text-gray-400 space-y-2">
          {[
            "Automatically reviews every PR with detailed feedback",
            "Analyzes issues and proposes solutions before fixing",
            "Proactive codebase patrol for bugs and security issues",
            "Proof-of-Work evidence for every change",
          ].map((f) => (
            <li key={f} className="flex items-start gap-2">
              <span className="text-green-400 mt-0.5">✓</span>
              {f}
            </li>
          ))}
        </ul>

        {/* Login button */}
        <a
          href={`${API_URL}/auth/github`}
          className="block w-full bg-white text-gray-900 font-semibold py-3 px-6 rounded-lg hover:bg-gray-100 transition-colors"
        >
          Login with GitHub
        </a>

        <p className="text-xs text-gray-600">
          By signing in you agree to our Terms of Service.
        </p>
      </div>
    </main>
  );
}
