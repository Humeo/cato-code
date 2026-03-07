import type { User, Stats, Repo, Activity } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}${path}`, {
      credentials: "include", // send session cookie
      ...init,
    });
    if (res.status === 401) return null;
    if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

export async function getMe(): Promise<User | null> {
  return apiFetch<User>("/api/me");
}

export async function getStats(): Promise<Stats | null> {
  return apiFetch<Stats>("/api/stats");
}

export async function getRepos(): Promise<Repo[] | null> {
  return apiFetch<Repo[]>("/api/repos");
}

export async function getActivities(): Promise<Activity[] | null> {
  return apiFetch<Activity[]>("/api/activities");
}

export async function getInstallUrl(): Promise<string | null> {
  const data = await apiFetch<{ url: string }>("/api/install-url");
  return data?.url ?? null;
}

export async function logout(): Promise<void> {
  await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}
