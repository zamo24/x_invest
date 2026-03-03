"use client";

import { FormEvent, KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { Folder, LibraryThreadListItem } from "@/lib/types";

type ChatFormProps = {
  message: string;
  scope: "all" | "thread";
  threadId: string;
  folderId: string;
  threads: LibraryThreadListItem[];
  folders: Folder[];
  loading: boolean;
  onMessageChange: (value: string) => void;
  onScopeChange: (value: "all" | "thread") => void;
  onThreadChange: (value: string) => void;
  onFolderChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

function truncateLabel(value: string, maxLength = 80) {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 3)}...`;
}

export function ChatForm({
  message,
  scope,
  threadId,
  folderId,
  threads,
  folders,
  loading,
  onMessageChange,
  onScopeChange,
  onThreadChange,
  onFolderChange,
  onSubmit,
}: ChatFormProps) {
  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto w-full max-w-3xl space-y-3 px-4 pb-4 sm:px-8 sm:pb-6">
      <div className="grid gap-2 pt-2 sm:grid-cols-2 lg:grid-cols-3">
        <Select id="chat-scope" value={scope} onChange={(event) => onScopeChange(event.target.value as "all" | "thread")}>
          <option value="all">Scope: All saved items</option>
          <option value="thread">Scope: Single thread</option>
        </Select>

        <Select id="chat-folder" value={folderId} onChange={(event) => onFolderChange(event.target.value)}>
          <option value="">Folder: All folders</option>
          {folders.map((folder) => (
            <option key={folder.id} value={folder.id}>
              {folder.name}
            </option>
          ))}
        </Select>

        {scope === "thread" ? (
          <Select id="chat-thread" value={threadId} onChange={(event) => onThreadChange(event.target.value)}>
            <option value="">Thread: Select thread...</option>
            {threads.map((thread) => (
              <option key={thread.id} value={thread.id} title={thread.title}>
                {truncateLabel(thread.title)}
              </option>
            ))}
          </Select>
        ) : (
          <div />
        )}
      </div>

      <div className="rounded-2xl border border-slate-300 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <Textarea
          id="chat-message"
          value={message}
          onChange={(event) => onMessageChange(event.target.value)}
          onKeyDown={onComposerKeyDown}
          rows={3}
          placeholder="Message Investor Copilot..."
          className="min-h-[96px] resize-none border-0 p-0 shadow-none focus-visible:ring-0"
        />
        <div className="mt-2 flex items-center justify-end">
          <Button type="submit" disabled={loading || !message.trim() || (scope === "thread" && !threadId)}>
            {loading ? "Sending..." : "Send"}
          </Button>
        </div>
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">Press Enter to send, Shift+Enter for a new line.</p>
    </form>
  );
}
