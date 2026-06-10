import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/server-api";

export async function POST(request: Request) {
  const response = await apiFetch("/v1/sources/x", { method: "POST", body: await request.text() });
  return NextResponse.json(await response.json(), { status: response.status });
}
