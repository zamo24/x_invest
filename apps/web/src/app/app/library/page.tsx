"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { LibraryItem, LibraryThreadListItem } from "@/lib/types";

export default function LibraryPage() {
  const [threads, setThreads] = useState<LibraryThreadListItem[]>([]);
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [threadsRes, itemsRes] = await Promise.all([
          fetch("/api/library/threads", { cache: "no-store" }),
          fetch("/api/library/items", { cache: "no-store" }),
        ]);

        if (!threadsRes.ok || !itemsRes.ok) {
          throw new Error("Failed to load library");
        }

        const threadsJson = (await threadsRes.json()) as LibraryThreadListItem[];
        const itemsJson = (await itemsRes.json()) as LibraryItem[];

        setThreads(threadsJson);
        setItems(itemsJson);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  if (loading) {
    return <p>Loading library...</p>;
  }

  if (error) {
    return <p className="error">{error}</p>;
  }

  return (
    <section className="grid">
      <article className="panel">
        <h2>Saved Threads</h2>
        {threads.length === 0 && <p>No threads yet. Use the extension to save a thread from X.</p>}
        <ul>
          {threads.map((thread) => (
            <li key={thread.id} className="list-row">
              <div>
                <Link href={`/app/threads/${thread.id}`}>{thread.title}</Link>
                <p>
                  {thread.item_count} items {thread.is_partial ? "• partial capture" : ""}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </article>

      <article className="panel">
        <h2>Latest Saved Tweets</h2>
        {items.length === 0 && <p>No tweets saved yet.</p>}
        <ul>
          {items.slice(0, 20).map((item) => (
            <li key={item.id} className="list-row">
              <a href={item.url} target="_blank" rel="noreferrer">
                @{item.author_handle}
              </a>
              <p>{item.text}</p>
            </li>
          ))}
        </ul>
      </article>
    </section>
  );
}


