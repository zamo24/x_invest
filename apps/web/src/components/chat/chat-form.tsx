"use client";

import { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { Folder, LibraryThreadListItem } from "@/lib/types";

type ChatFormProps = {
  message: string;
  hasActiveChatThread: boolean;
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
  onStartNewThread: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

function truncateLabel(value: string, maxLength = 72) {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 3)}...`;
}

export function ChatForm({
  message,
  hasActiveChatThread,
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
  onStartNewThread,
  onSubmit,
}: ChatFormProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Investor Copilot Chat</CardTitle>
        <CardDescription>
          Answers are generated from your saved sources only.
          {hasActiveChatThread ? " Follow-ups will continue the selected chat thread." : " Your first prompt creates a new thread."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="chat-message" className="text-sm font-medium text-slate-800">
              Message
            </label>
            <Textarea
              id="chat-message"
              value={message}
              onChange={(event) => onMessageChange(event.target.value)}
              rows={6}
              placeholder="Summarize my latest semiconductor takes."
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="min-w-0 space-y-2">
              <label htmlFor="chat-scope" className="text-sm font-medium text-slate-800">
                Scope
              </label>
              <Select
                id="chat-scope"
                value={scope}
                onChange={(event) => onScopeChange(event.target.value as "all" | "thread")}
              >
                <option value="all">All saved items</option>
                <option value="thread">Single thread</option>
              </Select>
            </div>

            <div className="min-w-0 space-y-2">
              <label htmlFor="chat-folder" className="text-sm font-medium text-slate-800">
                Folder (optional)
              </label>
              <Select id="chat-folder" value={folderId} onChange={(event) => onFolderChange(event.target.value)}>
                <option value="">All folders</option>
                {folders.map((folder) => (
                  <option key={folder.id} value={folder.id}>
                    {folder.name}
                  </option>
                ))}
              </Select>
            </div>

            {scope === "thread" ? (
              <div className="min-w-0 space-y-2">
                <label htmlFor="chat-thread" className="text-sm font-medium text-slate-800">
                  Thread
                </label>
                <Select id="chat-thread" value={threadId} onChange={(event) => onThreadChange(event.target.value)}>
                  <option value="">Select thread...</option>
                  {threads.map((thread) => (
                    <option key={thread.id} value={thread.id} title={thread.title}>
                      {truncateLabel(thread.title)}
                    </option>
                  ))}
                </Select>
              </div>
            ) : null}
          </div>

          <Button type="submit" disabled={loading || (scope === "thread" && !threadId)}>
            {loading ? "Running..." : "Ask Copilot"}
          </Button>
          <Button type="button" variant="outline" onClick={onStartNewThread}>
            Start New Chat Thread
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
