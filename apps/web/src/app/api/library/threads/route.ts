import { NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const limit = url.searchParams.get("limit") ?? "50";
  const offset = url.searchParams.get("offset") ?? "0";
  const folderId = url.searchParams.get("folder_id");
  const unassigned = url.searchParams.get("unassigned");

  const params = new URLSearchParams({ limit, offset });
  if (folderId) {
    params.set("folder_id", folderId);
  }
  if (unassigned) {
    params.set("unassigned", unassigned);
  }

  const response = await apiFetch(`/v1/library/threads?${params.toString()}`);
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
