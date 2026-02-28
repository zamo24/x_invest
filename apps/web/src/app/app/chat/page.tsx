"use client";

import { FormEvent, useEffect, useState } from "react";

import type { ChatSource, LibraryThreadListItem } from "@/lib/types";

type ChatResult = {
  answer_text: string;
  cited_sources: ChatSource[];
};

export default function ChatPage() {
  const [message, setMessage] = useState("Summarize my latest semiconductor takes.");
  const [scope, setScope] = useState<"all" | "thread">("all");
  const [threadId, setThreadId] = useState("");
  const [threads, setThreads] = useState<LibraryThreadListItem[]>([]);
  const [result, setResult] = useState<ChatResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadThreads() {
      const res = await fetch("/api/library/threads", { cache: "no-store" });
      if (!res.ok) return;
      setThreads((await res.json()) as LibraryThreadListItem[]);
    }

    void loadThreads();
  }, []);

  async function onSubmit(event: FormEvent) {
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

      setResult((await res.json()) as ChatResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Investor Copilot Chat</h2>
      <form onSubmit={onSubmit} className="chat-form">
        <textarea value={message} onChange={(event) => setMessage(event.target.value)} rows={5} />
        <div className="form-row">
          <label>
            Scope
            <select value={scope} onChange={(event) => setScope(event.target.value as "all" | "thread")}>
              <option value="all">All saved items</option>
              <option value="thread">Single thread</option>
            </select>
          </label>

          {scope === "thread" && (
            <label>
              Thread
              <select value={threadId} onChange={(event) => setThreadId(event.target.value)}>
                <option value="">Select thread...</option>
                {threads.map((thread) => (
                  <option key={thread.id} value={thread.id}>
                    {thread.title}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <button className="primary" type="submit" disabled={loading}>
          {loading ? "Running..." : "Ask Copilot"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="chat-result">
          <h3>Answer</h3>
          <pre>{result.answer_text}</pre>

          <h3>Sources Used</h3>
          <ul>
            {result.cited_sources.map((source) => (
              <li key={source.tweet_url}>
                <a href={source.tweet_url} target="_blank" rel="noreferrer">
                  {source.tweet_url}
                </a>
                <p>{source.snippet}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
