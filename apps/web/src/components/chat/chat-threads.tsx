"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ChatThreadListItem } from "@/lib/types";

type ChatThreadsProps = {
  threads: ChatThreadListItem[];
  selectedThreadId: string;
  onSelectThread: (threadId: string) => void;
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

export function ChatThreads({ threads, selectedThreadId, onSelectThread }: ChatThreadsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Saved Chat Threads</CardTitle>
        <CardDescription>Threads are auto-saved every time you ask Copilot.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {threads.length === 0 ? (
          <p className="text-sm text-slate-600">No chat threads yet.</p>
        ) : (
          threads.map((thread) => (
            <button
              key={thread.id}
              type="button"
              onClick={() => onSelectThread(thread.id)}
              className={cn(
                "w-full rounded-md border px-3 py-2 text-left",
                selectedThreadId === thread.id
                  ? "border-emerald-400 bg-emerald-50"
                  : "border-slate-200 bg-white hover:border-slate-300",
              )}
            >
              <p className="truncate text-sm font-medium text-slate-900">{thread.title}</p>
              <p className="text-xs text-slate-500">
                {thread.message_count} messages - {formatDate(thread.last_message_at)}
              </p>
            </button>
          ))
        )}
      </CardContent>
    </Card>
  );
}
