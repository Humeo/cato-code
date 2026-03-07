"use client";

import { logout } from "@/lib/api";
import { useRouter } from "next/navigation";
import type { User } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface UserNavProps {
  user: User;
}

export function UserNav({ user }: UserNavProps) {
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.push("/");
    router.refresh();
  }

  return (
    <div className="flex items-center gap-3">
      {user.avatar_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={user.avatar_url}
          alt={user.github_login}
          className="w-8 h-8 rounded-full"
        />
      )}
      <span className="text-sm text-gray-300">{user.github_login}</span>
      <button
        onClick={handleLogout}
        className="text-xs text-gray-500 hover:text-gray-300 border border-gray-700 px-2 py-1 rounded"
      >
        Sign out
      </button>
    </div>
  );
}
