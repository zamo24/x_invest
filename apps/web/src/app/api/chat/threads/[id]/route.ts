import { NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

type Params = {
  params: Promise<{ id: string }>;
};

export async function GET(_: Request, { params }: Params) {
  const { id } = await params;
  const response = await apiFetch(`/v1/chat/threads/${id}`);
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}

export async function PATCH(request: Request, { params }: Params) {
  const { id } = await params;
  const body = await request.json();
  const response = await apiFetch(`/v1/chat/threads/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}

export async function DELETE(_: Request, { params }: Params) {
  const { id } = await params;
  const response = await apiFetch(`/v1/chat/threads/${id}`, { method: "DELETE" });
  if (response.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
