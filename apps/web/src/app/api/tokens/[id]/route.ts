import { NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

type Params = { params: Promise<{ id: string }> };

export async function DELETE(_request: Request, { params }: Params) {
  const { id } = await params;
  const response = await apiFetch(`/v1/tokens/${id}`, { method: "DELETE" });
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
