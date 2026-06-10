import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/server-api";

export async function DELETE() {
  const response = await apiFetch("/v1/integrations/x", { method: "DELETE" });
  return NextResponse.json(await response.json(), { status: response.status });
}
