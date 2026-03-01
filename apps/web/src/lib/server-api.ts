import { auth } from "@clerk/nextjs/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

async function getForwardHeaders() {
  const { userId, getToken } = await auth();
  if (!userId) {
    return null;
  }

  const sessionToken = await getToken();
  if (!sessionToken) {
    return null;
  }

  const headers = new Headers();
  headers.set("authorization", `Bearer ${sessionToken}`);

  return headers;
}

export async function apiFetch(path: string, init?: RequestInit) {
  const clerkHeaders = await getForwardHeaders();
  if (!clerkHeaders) {
    return new Response(JSON.stringify({ detail: "Not authenticated" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

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
