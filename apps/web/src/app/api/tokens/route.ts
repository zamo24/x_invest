import { NextRequest, NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

export async function GET() {
  const response = await apiFetch("/v1/tokens");
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await apiFetch("/v1/tokens", {
    method: "POST",
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
