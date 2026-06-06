"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { ChatForm } from "@/components/chat/chat-form";
import { ChatHistory } from "@/components/chat/chat-history";
import { ChatThreads } from "@/components/chat/chat-threads";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { ChatMessageItem, ChatThreadDetail, ChatThreadListItem, Folder, LibraryThreadListItem } from "@/lib/types";

type ChatResultPayload = {
  chat_thread_id: string | null;
};

const THREAD_PAGE_SIZE = 12;

async function fetchChatThreadsPage(offset: number): Promise<ChatThreadListItem[] | null> {
  const chatThreadsRes = await fetch(`/api/chat/threads?limit=${THREAD_PAGE_SIZE}&offset=${offset}`, {
    cache: "no-store",
  });
  if (!chatThreadsRes.ok) {
    return null;
  }

  return (await chatThreadsRes.json()) as ChatThreadListItem[];
}

function buildOptimisticUserMessage(text: string): ChatMessageItem {
  return {
    id: `temp-user-${Date.now()}`,
    role: "user",
    message_text: text,
    cited_sources: [],
    provider_used: null,
    model_used: null,
    inference_mode_used: null,
    reasoning_effort_used: null,
    created_at: new Date().toISOString(),
  };
}

export default function ChatPage() {
  const [message, setMessage] = useState("");
  const [scope, setScope] = useState<"all" | "thread">("all");
  const [threadId, setThreadId] = useState("");
  const [folderId, setFolderId] = useState("");
  const [chatThreadId, setChatThreadId] = useState("");
  const [chatThreadOffset, setChatThreadOffset] = useState(0);
  const [hasMoreChatThreads, setHasMoreChatThreads] = useState(false);
  const [threads, setThreads] = useState<LibraryThreadListItem[]>([]);
  const [chatThreads, setChatThreads] = useState<ChatThreadListItem[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessageItem[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(false);
  const [threadOpsLoading, setThreadOpsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentThreadTitle = useMemo(() => {
    if (!chatThreadId) {
      return "New chat";
    }
    const selected = chatThreads.find((thread) => thread.id === chatThreadId);
    return selected?.title || "Saved chat";
  }, [chatThreadId, chatThreads]);

  function upsertSidebarThread(thread: ChatThreadListItem) {
    setChatThreads((current) => {
      const next = [thread, ...current.filter((entry) => entry.id !== thread.id)];
      return next.slice(0, THREAD_PAGE_SIZE);
    });
  }

  const loadChatThreads = useCallback(
    async (offset: number, preferredThreadId?: string) => {
      const payload = await fetchChatThreadsPage(offset);
      if (!payload) {
        return;
      }

      setChatThreads(payload);
      setHasMoreChatThreads(payload.length === THREAD_PAGE_SIZE);

      const preferred = preferredThreadId ?? chatThreadId;
      if (payload.length === 0) {
        setChatThreadId("");
        return;
      }

      if (preferred && payload.some((thread) => thread.id === preferred)) {
        setChatThreadId(preferred);
        return;
      }

      if (!chatThreadId) {
        setChatThreadId(payload[0].id);
      }
    },
    [chatThreadId],
  );

  const loadChatThreadDetail = useCallback(async (activeThreadId: string): Promise<ChatThreadDetail | null> => {
    if (!activeThreadId) {
      setChatMessages([]);
      return null;
    }

    const detailRes = await fetch(`/api/chat/threads/${activeThreadId}`, { cache: "no-store" });
    if (!detailRes.ok) {
      setChatMessages([]);
      return null;
    }
    const payload = (await detailRes.json()) as ChatThreadDetail;
    setChatMessages(payload.messages);
    return payload;
  }, []);

  useEffect(() => {
    async function loadData() {
      const [threadsRes, foldersRes, chatThreadPayload] = await Promise.all([
        fetch("/api/library/threads", { cache: "no-store" }),
        fetch("/api/library/folders", { cache: "no-store" }),
        fetchChatThreadsPage(0),
      ]);

      if (threadsRes.ok) {
        setThreads((await threadsRes.json()) as LibraryThreadListItem[]);
      }
      if (foldersRes.ok) {
        setFolders((await foldersRes.json()) as Folder[]);
      }
      if (!chatThreadPayload) {
        return;
      }

      setChatThreads(chatThreadPayload);
      setHasMoreChatThreads(chatThreadPayload.length === THREAD_PAGE_SIZE);
      if (chatThreadPayload.length > 0) {
        setChatThreadId(chatThreadPayload[0].id);
      }
    }

    void loadData().catch(() => undefined);
  }, []);

  useEffect(() => {
    void loadChatThreadDetail(chatThreadId);
  }, [chatThreadId, loadChatThreadDetail]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedMessage = message.trim();
    if (!trimmedMessage) {
      return;
    }

    const optimisticUserMessage = buildOptimisticUserMessage(trimmedMessage);
    setChatMessages((current) => [...current, optimisticUserMessage]);
    setMessage("");
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message: trimmedMessage,
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
      const activeThreadId = payload.chat_thread_id || chatThreadId;
      setChatThreadOffset(0);
      await loadChatThreads(0, activeThreadId || undefined);
      const detail = await loadChatThreadDetail(activeThreadId || "");
      if (detail?.thread) {
        upsertSidebarThread(detail.thread);
      }
    } catch (err) {
      setChatMessages((current) => current.filter((entry) => entry.id !== optimisticUserMessage.id));
      setMessage(trimmedMessage);
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function onRenameChatThread(threadIdToRename: string, title: string) {
    setThreadOpsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/chat/threads/${threadIdToRename}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ title }),
      });
      if (!response.ok) {
        const maybeJson = await response.json().catch(() => ({}));
        throw new Error(maybeJson?.detail || "Failed to rename chat thread");
      }
      await loadChatThreads(chatThreadOffset, threadIdToRename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setThreadOpsLoading(false);
    }
  }

  async function onDeleteChatThread(threadIdToDelete: string) {
    setThreadOpsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/chat/threads/${threadIdToDelete}`, { method: "DELETE" });
      if (!response.ok) {
        const maybeJson = await response.json().catch(() => ({}));
        throw new Error(maybeJson?.detail || "Failed to delete chat thread");
      }

      const deletingSelectedThread = chatThreadId === threadIdToDelete;
      const shouldMoveToPreviousPage = chatThreads.length === 1 && chatThreadOffset > 0;
      const nextOffset = shouldMoveToPreviousPage ? Math.max(0, chatThreadOffset - THREAD_PAGE_SIZE) : chatThreadOffset;
      setChatThreadOffset(nextOffset);

      if (deletingSelectedThread) {
        setChatMessages([]);
      }

      await loadChatThreads(nextOffset, deletingSelectedThread ? undefined : chatThreadId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setThreadOpsLoading(false);
    }
  }

  async function onNextThreadPage() {
    if (!hasMoreChatThreads || threadOpsLoading || loading) {
      return;
    }
    const nextOffset = chatThreadOffset + THREAD_PAGE_SIZE;
    setChatThreadOffset(nextOffset);
    await loadChatThreads(nextOffset);
  }

  async function onPrevThreadPage() {
    if (chatThreadOffset === 0 || threadOpsLoading || loading) {
      return;
    }
    const nextOffset = Math.max(0, chatThreadOffset - THREAD_PAGE_SIZE);
    setChatThreadOffset(nextOffset);
    await loadChatThreads(nextOffset);
  }

  function onStartNewThread() {
    setChatThreadId("");
    setChatMessages([]);
    setError(null);
  }

  return (
    <section className="h-[calc(100vh-9rem)] min-h-[620px]">
      {error ? (
        <Alert variant="destructive" className="mb-4">
          <AlertTitle>Chat request failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid h-full gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
        <ChatThreads
          threads={chatThreads}
          selectedThreadId={chatThreadId}
          isUpdating={threadOpsLoading || loading}
          canGoPrev={chatThreadOffset > 0}
          canGoNext={hasMoreChatThreads}
          onStartNewThread={onStartNewThread}
          onSelectThread={setChatThreadId}
          onRenameThread={onRenameChatThread}
          onDeleteThread={onDeleteChatThread}
          onPrevPage={() => void onPrevThreadPage()}
          onNextPage={() => void onNextThreadPage()}
        />

        <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/40">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800 sm:px-6">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Investor Copilot</p>
              <p className="max-w-[70vw] truncate text-sm font-semibold text-slate-900 dark:text-slate-100">{currentThreadTitle}</p>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={onStartNewThread} disabled={loading || threadOpsLoading}>
              New chat
            </Button>
          </div>

          <ChatHistory messages={chatMessages} loading={loading} />

          <div className="border-t border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/40">
            <ChatForm
              message={message}
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
              onSubmit={onSubmit}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
