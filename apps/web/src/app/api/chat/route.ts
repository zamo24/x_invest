import { NextRequest, NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await apiFetch("/v1/chat", {
    method: "POST",
    body: JSON.stringify(body),
  });

  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
