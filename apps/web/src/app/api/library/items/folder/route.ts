import { NextRequest, NextResponse } from "next/server";

import { apiFetch } from "@/lib/server-api";

type AssignItemFolderRequest = {
  item_id: string;
  folder_id: string | null;
};

export async function PATCH(request: NextRequest) {
  const body = (await request.json()) as AssignItemFolderRequest;
  const response = await apiFetch(`/v1/library/items/${body.item_id}/folder`, {
    method: "PATCH",
    body: JSON.stringify({ folder_id: body.folder_id }),
  });
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
