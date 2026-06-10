import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/server-api";

export async function POST() {
  const response = await apiFetch("/v1/integrations/x/bookmarks/sync", { method: "POST" });
  return NextResponse.json(await response.json(), { status: response.status });
}
