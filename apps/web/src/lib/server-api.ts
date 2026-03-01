import { auth } from "@clerk/nextjs/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
const CLERK_JWT_TEMPLATE = process.env.CLERK_JWT_TEMPLATE;

type ClerkTokenOptions = {
  skipCache?: boolean;
  template?: string;
};

async function getSessionToken(forceRefresh = false): Promise<string | null> {
  const { userId, getToken } = await auth();
  if (!userId) {
    return null;
  }

  // Clerk type signatures vary by package/runtime version, so pass options via a narrow local type.
  const options: ClerkTokenOptions = {};
  if (forceRefresh) {
    options.skipCache = true;
  }
  if (CLERK_JWT_TEMPLATE) {
    options.template = CLERK_JWT_TEMPLATE;
  }

  const token = await getToken(options);
  if (!token) {
    return null;
  }

  return token;
}

function buildAuthHeaders(sessionToken: string) {
  const headers = new Headers();
  headers.set("authorization", `Bearer ${sessionToken}`);
  return headers;
}

function mergeHeaders(initHeaders: RequestInit["headers"], authHeaders: Headers) {
  const headers = new Headers(initHeaders);
  authHeaders.forEach((value, key) => headers.set(key, value));
  return headers;
}

export async function apiFetch(path: string, init?: RequestInit) {
  const firstToken = await getSessionToken(false);
  if (!firstToken) {
    return new Response(JSON.stringify({ detail: "Not authenticated" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  const firstHeaders = mergeHeaders(init?.headers, buildAuthHeaders(firstToken));
  if (!firstHeaders.has("content-type") && init?.body) {
    firstHeaders.set("content-type", "application/json");
  }
  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: firstHeaders,
    cache: "no-store",
  });

  if (response.status !== 401) {
    return response;
  }

  const refreshedToken = await getSessionToken(true);
  if (!refreshedToken || refreshedToken === firstToken) {
    return response;
  }

  const retryHeaders = mergeHeaders(init?.headers, buildAuthHeaders(refreshedToken));
  if (!retryHeaders.has("content-type") && init?.body) {
    retryHeaders.set("content-type", "application/json");
  }
  response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: retryHeaders,
    cache: "no-store",
  });

  return response;
}
