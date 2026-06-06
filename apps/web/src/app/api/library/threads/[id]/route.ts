import { NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

type Params = { params: Promise<{ id: string }> };

export async function GET(_request: Request, { params }: Params) {
  const { id } = await params;
  const requestUrl = new URL(_request.url);
  const version = requestUrl.searchParams.get("version");
  const query = version ? `?version=${encodeURIComponent(version)}` : "";
  const response = await apiFetch(`/v1/library/threads/${id}${query}`);
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
