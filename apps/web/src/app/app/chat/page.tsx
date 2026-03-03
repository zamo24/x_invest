"use client";

import { FormEvent, useEffect, useState } from "react";

import { ChatForm } from "@/components/chat/chat-form";
import { ChatHistory } from "@/components/chat/chat-history";
import { ChatResult } from "@/components/chat/chat-result";
import { ChatThreads } from "@/components/chat/chat-threads";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type {
  ChatMessageItem,
  ChatSource,
  ChatThreadDetail,
  ChatThreadListItem,
  Folder,
  LibraryThreadListItem,
} from "@/lib/types";

type ChatResultPayload = {
  chat_thread_id: string | null;
  answer_text: string;
  cited_sources: ChatSource[];
};

export default function ChatPage() {
  const [message, setMessage] = useState("Summarize my latest semiconductor takes.");
  const [scope, setScope] = useState<"all" | "thread">("all");
  const [threadId, setThreadId] = useState("");
  const [folderId, setFolderId] = useState("");
  const [chatThreadId, setChatThreadId] = useState("");
  const [threads, setThreads] = useState<LibraryThreadListItem[]>([]);
  const [chatThreads, setChatThreads] = useState<ChatThreadListItem[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessageItem[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [result, setResult] = useState<ChatResultPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadChatThreads() {
    const chatThreadsRes = await fetch("/api/chat/threads", { cache: "no-store" });
    if (!chatThreadsRes.ok) {
      return;
    }
    const payload = (await chatThreadsRes.json()) as ChatThreadListItem[];
    setChatThreads(payload);
    if (!chatThreadId && payload.length > 0) {
      setChatThreadId(payload[0].id);
    }
  }

  async function loadChatThreadDetail(activeThreadId: string) {
    if (!activeThreadId) {
      setChatMessages([]);
      return;
    }

    const detailRes = await fetch(`/api/chat/threads/${activeThreadId}`, { cache: "no-store" });
    if (!detailRes.ok) {
      setChatMessages([]);
      return;
    }
    const payload = (await detailRes.json()) as ChatThreadDetail;
    setChatMessages(payload.messages);
  }

  useEffect(() => {
    async function loadData() {
      const [threadsRes, foldersRes] = await Promise.all([
        fetch("/api/library/threads", { cache: "no-store" }),
        fetch("/api/library/folders", { cache: "no-store" }),
      ]);

      if (threadsRes.ok) {
        setThreads((await threadsRes.json()) as LibraryThreadListItem[]);
      }
      if (foldersRes.ok) {
        setFolders((await foldersRes.json()) as Folder[]);
      }
      await loadChatThreads();
    }

    void loadData().catch(() => undefined);
  }, []);

  useEffect(() => {
    void loadChatThreadDetail(chatThreadId);
  }, [chatThreadId]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message,
          scope,
          thread_id: scope === "thread" ? threadId : undefined,
          chat_thread_id: chatThreadId || undefined,
          filters: folderId ? { folder_id: folderId } : undefined,
          top_k: 8,
        }),
      });

      if (!res.ok) {
        const maybeJson = await res.json().catch(() => ({}));
        throw new Error(maybeJson?.detail || "Chat request failed");
      }

      const payload = (await res.json()) as ChatResultPayload;
      setResult(payload);
      if (payload.chat_thread_id) {
        setChatThreadId(payload.chat_thread_id);
      }
      await loadChatThreads();
      await loadChatThreadDetail(payload.chat_thread_id || chatThreadId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  function onStartNewThread() {
    setChatThreadId("");
    setChatMessages([]);
    setResult(null);
  }

  return (
    <section className="space-y-6">
      <PageHeader
        title="Investor Copilot"
        description="Ask questions across your saved X corpus and review source-grounded citations."
      />

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Chat request failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <ChatThreads threads={chatThreads} selectedThreadId={chatThreadId} onSelectThread={setChatThreadId} />

        <div className="space-y-6">
          <ChatForm
            message={message}
            hasActiveChatThread={Boolean(chatThreadId)}
            scope={scope}
            threadId={threadId}
            folderId={folderId}
            threads={threads}
            folders={folders}
            loading={loading}
            onMessageChange={setMessage}
            onScopeChange={setScope}
            onThreadChange={setThreadId}
            onFolderChange={setFolderId}
            onStartNewThread={onStartNewThread}
            onSubmit={onSubmit}
          />

          <ChatHistory messages={chatMessages} />
          {result ? <ChatResult answerText={result.answer_text} sources={result.cited_sources} /> : null}
        </div>
      </div>
    </section>
  );
}
