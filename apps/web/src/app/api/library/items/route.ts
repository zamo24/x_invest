import { NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const limit = url.searchParams.get("limit") ?? "50";
  const offset = url.searchParams.get("offset") ?? "0";

  const response = await apiFetch(`/v1/library/items?limit=${limit}&offset=${offset}`);
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
