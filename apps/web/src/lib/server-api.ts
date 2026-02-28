import { auth, currentUser } from "@clerk/nextjs/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

async function getForwardHeaders() {
  const { userId } = await auth();
  if (!userId) {
    throw new Error("Not authenticated");
  }

  const user = await currentUser();
  const headers = new Headers();
  headers.set("x-clerk-user-id", userId);

  const email = user?.primaryEmailAddress?.emailAddress;
  if (email) {
    headers.set("x-clerk-email", email);
  }

  return headers;
}

export async function apiFetch(path: string, init?: RequestInit) {
  const clerkHeaders = await getForwardHeaders();
  const headers = new Headers(init?.headers);

  clerkHeaders.forEach((value, key) => headers.set(key, value));
  if (!headers.has("content-type") && init?.body) {
    headers.set("content-type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  return response;
}
