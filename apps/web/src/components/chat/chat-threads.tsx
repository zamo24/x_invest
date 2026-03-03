"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { ChatThreadListItem } from "@/lib/types";

type ChatThreadsProps = {
  threads: ChatThreadListItem[];
  selectedThreadId: string;
  isUpdating: boolean;
  canGoPrev: boolean;
  canGoNext: boolean;
  onStartNewThread: () => void;
  onSelectThread: (threadId: string) => void;
  onRenameThread: (threadId: string, title: string) => Promise<void>;
  onDeleteThread: (threadId: string) => Promise<void>;
  onPrevPage: () => void;
  onNextPage: () => void;
};

export function ChatThreads({
  threads,
  selectedThreadId,
  isUpdating,
  canGoPrev,
  canGoNext,
  onStartNewThread,
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
    <aside className="flex h-full w-full flex-col rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
      <div className="border-b border-slate-200 p-3 dark:border-slate-800">
        <Button type="button" className="w-full justify-start" onClick={onStartNewThread} disabled={isUpdating}>
          + New Chat
        </Button>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {threads.length === 0 ? (
          <p className="px-2 text-sm text-slate-500">No chats yet</p>
        ) : (
          threads.map((thread) => (
            <div
              key={thread.id}
              className={cn(
                "rounded-lg border p-2",
                selectedThreadId === thread.id
                  ? "border-emerald-400 bg-emerald-50 dark:bg-emerald-950/30"
                  : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950",
              )}
            >
              {editingThreadId === thread.id ? (
                <div className="space-y-2">
                  <Input
                    value={draftTitle}
                    onChange={(event) => setDraftTitle(event.target.value)}
                    maxLength={200}
                    autoFocus
                  />
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
                <div className="space-y-2">
                  <button type="button" onClick={() => onSelectThread(thread.id)} className="w-full text-left">
                    <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">{thread.title}</p>
                    <p className="text-xs text-slate-500">{thread.message_count} messages</p>
                  </button>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => beginRename(thread)}
                      disabled={isUpdating}
                    >
                      Rename
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => void handleDelete(thread)}
                      disabled={isUpdating}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="flex items-center justify-between border-t border-slate-200 p-3 dark:border-slate-800">
        <Button type="button" variant="outline" size="sm" onClick={onPrevPage} disabled={!canGoPrev || isUpdating}>
          Previous
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={onNextPage} disabled={!canGoNext || isUpdating}>
          Next
        </Button>
      </div>
    </aside>
  );
}
