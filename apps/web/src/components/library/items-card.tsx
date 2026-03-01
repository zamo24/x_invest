"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import type { Folder, LibraryItem } from "@/lib/types";
import { cn } from "@/lib/utils";

type ItemsCardProps = {
  items: LibraryItem[];
  folders: Folder[];
  assigningItemId: string | null;
  onAssignFolder: (itemId: string, folderId: string | null) => void;
};

function formatDate(value: string | null) {
  if (!value) {
    return "Unknown date";
  }

  const asDate = new Date(value);
  if (Number.isNaN(asDate.getTime())) {
    return "Unknown date";
  }

  return asDate.toLocaleString();
}

export function ItemsCard({ items, folders, assigningItemId, onAssignFolder }: ItemsCardProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  function toggleExpanded(itemId: string) {
    setExpandedIds((previous) => {
      const next = new Set(previous);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  }

  return (
    <Card className="flex h-full max-h-[70vh] flex-col">
      <CardHeader>
        <CardTitle>Latest Saved Tweets</CardTitle>
        <CardDescription>Recent tweet captures available for retrieval and chat.</CardDescription>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {items.length === 0 ? (
          <p className="text-sm text-slate-600">No tweets saved yet.</p>
        ) : (
          items.slice(0, 20).map((item, index) => (
            <div key={item.id} className="space-y-3">
              {index > 0 && <Separator />}
              <article className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-slate-900 hover:text-emerald-700"
                  >
                    @{item.author_handle}
                  </a>
                  <Badge variant="outline">{formatDate(item.created_at ?? item.captured_at)}</Badge>
                  {item.folder_name ? <Badge variant="secondary">{item.folder_name}</Badge> : null}
                </div>
                <div className="max-w-xs">
                  <Select
                    value={item.folder_id ?? ""}
                    disabled={assigningItemId === item.id}
                    onChange={(event) => onAssignFolder(item.id, event.target.value || null)}
                  >
                    <option value="">No folder</option>
                    {folders.map((folder) => (
                      <option key={folder.id} value={folder.id}>
                        {folder.name}
                      </option>
                    ))}
                  </Select>
                </div>
                <p
                  className={cn(
                    "text-sm whitespace-pre-wrap text-slate-700",
                    !expandedIds.has(item.id) && "line-clamp-3",
                  )}
                >
                  {item.text}
                </p>
                {item.text.length > 220 ? (
                  <Button
                    type="button"
                    variant="link"
                    size="sm"
                    className="h-auto px-0"
                    onClick={() => toggleExpanded(item.id)}
                  >
                    {expandedIds.has(item.id) ? "Show less" : "Show more"}
                  </Button>
                ) : null}
              </article>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
