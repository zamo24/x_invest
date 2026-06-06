"use client";

import { useEffect, useRef } from "react";

import type { ChatMessageItem } from "@/lib/types";

type ChatHistoryProps = {
  messages: ChatMessageItem[];
  loading: boolean;
};

const URL_RE = /(https?:\/\/[^\s]+)/g;

function formatDate(value: string) {
  const asDate = new Date(value);
  if (Number.isNaN(asDate.getTime())) {
    return "";
  }
  return asDate.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function renderTextWithLinks(text: string) {
  const parts = text.split(URL_RE);
  return parts.map((part, index) => {
    if (!part.startsWith("http://") && !part.startsWith("https://")) {
      return <span key={`${part}-${index}`}>{part}</span>;
    }

    let url = part;
    let trailing = "";
    while (url.length > 0 && [")", ",", ".", ";"].includes(url[url.length - 1])) {
      trailing = `${url[url.length - 1]}${trailing}`;
      url = url.slice(0, -1);
    }
    return (
      <span key={`${url}-${index}`}>
        <a href={url} target="_blank" rel="noreferrer" className="text-emerald-700 hover:underline dark:text-emerald-300">
          {url}
        </a>
        {trailing}
      </span>
    );
  });
}

export function ChatHistory({ messages, loading }: ChatHistoryProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
      {messages.length === 0 ? (
        <div className="mx-auto max-w-3xl rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
          Start a new chat or select a previous thread. Ask follow-up questions to continue the same conversation.
        </div>
      ) : (
        <div className="mx-auto flex max-w-3xl flex-col gap-5">
          {messages.map((message) => {
            const isUser = message.role === "user";
            return (
              <div key={message.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                <div
                  className={
                    isUser
                      ? "max-w-[85%] rounded-2xl bg-emerald-600 px-4 py-3 text-sm text-white"
                      : "max-w-[90%] rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
                  }
                >
                  <div className="whitespace-pre-wrap">{renderTextWithLinks(message.message_text)}</div>
                  <div className={isUser ? "mt-2 text-right text-[11px] text-emerald-100" : "mt-2 text-[11px] text-slate-500"}>
                    {formatDate(message.created_at)}
                  </div>
                  {!isUser && message.cited_sources.length > 0 ? (
                    <div className="mt-3 space-y-1 border-t border-slate-200 pt-2 dark:border-slate-700">
                      <p className="text-xs font-medium text-slate-600 dark:text-slate-300">Sources</p>
                      <ul className="space-y-1">
                        {message.cited_sources.map((source) => (
                          <li key={`${message.id}-${source.tweet_url}`}>
                            <a
                              href={source.tweet_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-xs text-emerald-700 hover:underline dark:text-emerald-300"
                            >
                              {source.tweet_url}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}

          {loading ? (
            <div className="flex justify-start">
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                Copilot is thinking...
              </div>
            </div>
          ) : null}
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
