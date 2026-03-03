"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { ChatThreadListItem } from "@/lib/types";

type ChatThreadsProps = {
  threads: ChatThreadListItem[];
  selectedThreadId: string;
  isUpdating: boolean;
  canGoPrev: boolean;
  canGoNext: boolean;
  onSelectThread: (threadId: string) => void;
  onRenameThread: (threadId: string, title: string) => Promise<void>;
  onDeleteThread: (threadId: string) => Promise<void>;
  onPrevPage: () => void;
  onNextPage: () => void;
};

function formatDate(value: string | null) {
  if (!value) {
    return "No messages yet";
  }
  const asDate = new Date(value);
  if (Number.isNaN(asDate.getTime())) {
    return "Unknown";
  }
  return asDate.toLocaleString();
}

export function ChatThreads({
  threads,
  selectedThreadId,
  isUpdating,
  canGoPrev,
  canGoNext,
  onSelectThread,
  onRenameThread,
  onDeleteThread,
  onPrevPage,
  onNextPage,
}: ChatThreadsProps) {
  const [editingThreadId, setEditingThreadId] = useState("");
  const [draftTitle, setDraftTitle] = useState("");

  function beginRename(thread: ChatThreadListItem) {
    setEditingThreadId(thread.id);
    setDraftTitle(thread.title);
  }

  async function saveRename(threadId: string) {
    const trimmed = draftTitle.trim();
    if (!trimmed) {
      return;
    }
    await onRenameThread(threadId, trimmed);
    setEditingThreadId("");
  }

  async function handleDelete(thread: ChatThreadListItem) {
    const confirmed = window.confirm(`Delete chat thread "${thread.title}"? This cannot be undone.`);
    if (!confirmed) {
      return;
    }
    await onDeleteThread(thread.id);
    if (editingThreadId === thread.id) {
      setEditingThreadId("");
      setDraftTitle("");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Saved Chat Threads</CardTitle>
        <CardDescription>Threads are auto-saved every time you ask Copilot.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {threads.length === 0 ? (
          <p className="text-sm text-slate-600">No chat threads yet.</p>
        ) : (
          threads.map((thread) => (
            <div
              key={thread.id}
              className={cn(
                "space-y-2 rounded-md border p-2",
                selectedThreadId === thread.id ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-white",
              )}
            >
              <button type="button" onClick={() => onSelectThread(thread.id)} className="w-full text-left">
                <p className="truncate text-sm font-medium text-slate-900">{thread.title}</p>
                <p className="text-xs text-slate-500">
                  {thread.message_count} messages - {formatDate(thread.last_message_at)}
                </p>
              </button>

              {editingThreadId === thread.id ? (
                <div className="space-y-2">
                  <Input value={draftTitle} onChange={(event) => setDraftTitle(event.target.value)} maxLength={200} />
                  <div className="flex gap-2">
                    <Button type="button" size="sm" onClick={() => void saveRename(thread.id)} disabled={isUpdating}>
                      Save
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => setEditingThreadId("")}
                      disabled={isUpdating}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => beginRename(thread)}
                    disabled={isUpdating}
                  >
                    Rename
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="destructive"
                    onClick={() => void handleDelete(thread)}
                    disabled={isUpdating}
                  >
                    Delete
                  </Button>
                </div>
              )}
            </div>
          ))
        )}

        <div className="flex items-center justify-between pt-1">
          <Button type="button" variant="outline" size="sm" onClick={onPrevPage} disabled={!canGoPrev || isUpdating}>
            Previous
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={onNextPage} disabled={!canGoNext || isUpdating}>
            Next
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
