import { getInstallUrl } from "@/lib/api";

export default async function InstallPage() {
  const installUrl = await getInstallUrl();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-lg w-full text-center space-y-6">
        <span className="text-5xl">⚙️</span>
        <h1 className="text-3xl font-bold text-white">Install GitHub App</h1>
        <p className="text-gray-400">
          Install CatoCode on your GitHub account or organization to automatically
          watch repositories and start reviewing PRs and triaging issues.
        </p>

        <div className="bg-gray-800 rounded-lg p-4 text-left text-sm space-y-2">
          <p className="text-gray-300 font-semibold">What happens after installation:</p>
          <ul className="text-gray-400 space-y-1">
            {[
              "Selected repositories are automatically watched",
              "New pull requests trigger code reviews",
              "New issues trigger analysis and solution proposals",
              "Scheduled patrols scan for bugs and security issues",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-green-400">✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        {installUrl ? (
          <a
            href={installUrl}
            className="block w-full bg-green-600 hover:bg-green-500 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            Install on GitHub
          </a>
        ) : (
          <p className="text-red-400">Failed to generate install URL. Check backend config.</p>
        )}

        <a href="/dashboard" className="text-sm text-gray-500 hover:text-gray-300">
          ← Back to dashboard
        </a>
      </div>
    </main>
  );
}
