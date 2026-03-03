import { NextRequest, NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const limit = searchParams.get("limit");
  const offset = searchParams.get("offset");
  const query = new URLSearchParams();
  if (limit) {
    query.set("limit", limit);
  }
  if (offset) {
    query.set("offset", offset);
  }

  const path = query.size ? `/v1/chat/threads?${query.toString()}` : "/v1/chat/threads";
  const response = await apiFetch(path);
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
