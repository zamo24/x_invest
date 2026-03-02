import { NextRequest, NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

export async function GET() {
  const response = await apiFetch("/v1/model-settings");
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}

export async function PUT(request: NextRequest) {
  const body = await request.json();
  const response = await apiFetch("/v1/model-settings", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
