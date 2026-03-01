"use client";

import { FormEvent, useEffect, useState } from "react";

import { ChatForm } from "@/components/chat/chat-form";
import { ChatResult } from "@/components/chat/chat-result";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { ChatSource, LibraryThreadListItem } from "@/lib/types";

type ChatResultPayload = {
  answer_text: string;
  cited_sources: ChatSource[];
};

export default function ChatPage() {
  const [message, setMessage] = useState("Summarize my latest semiconductor takes.");
  const [scope, setScope] = useState<"all" | "thread">("all");
  const [threadId, setThreadId] = useState("");
  const [threads, setThreads] = useState<LibraryThreadListItem[]>([]);
  const [result, setResult] = useState<ChatResultPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadThreads() {
      const res = await fetch("/api/library/threads", { cache: "no-store" });
      if (!res.ok) {
        return;
      }

      setThreads((await res.json()) as LibraryThreadListItem[]);
    }

    void loadThreads();
  }, []);

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
          top_k: 8,
        }),
      });

      if (!res.ok) {
        const maybeJson = await res.json().catch(() => ({}));
        throw new Error(maybeJson?.detail || "Chat request failed");
      }

      setResult((await res.json()) as ChatResultPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
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

      <ChatForm
        message={message}
        scope={scope}
        threadId={threadId}
        threads={threads}
        loading={loading}
        onMessageChange={setMessage}
        onScopeChange={setScope}
        onThreadChange={setThreadId}
        onSubmit={onSubmit}
      />

      {result ? <ChatResult answerText={result.answer_text} sources={result.cited_sources} /> : null}
    </section>
  );
}
