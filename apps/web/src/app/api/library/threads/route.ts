import { NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const limit = url.searchParams.get("limit") ?? "50";
  const offset = url.searchParams.get("offset") ?? "0";
  const folderId = url.searchParams.get("folder_id");
  const unassigned = url.searchParams.get("unassigned");
  const q = url.searchParams.get("q");
  const authorHandle = url.searchParams.get("author_handle");

  const params = new URLSearchParams({ limit, offset });
  if (folderId) {
    params.set("folder_id", folderId);
  }
  if (unassigned) {
    params.set("unassigned", unassigned);
  }
  if (q) {
    params.set("q", q);
  }
  if (authorHandle) {
    params.set("author_handle", authorHandle);
  }

  const response = await apiFetch(`/v1/library/threads?${params.toString()}`);
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
