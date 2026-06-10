import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/server-api";

export async function GET() {
  const response = await apiFetch("/v1/integrations/x/status");
  return NextResponse.json(await response.json(), { status: response.status });
}
