import { NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

export async function GET() {
  const response = await apiFetch("/v1/chat/threads");
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
