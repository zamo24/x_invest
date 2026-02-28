"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import type { LibraryItem, LibraryThreadListItem } from "@/lib/types";

type ThreadResponse = {
  thread: LibraryThreadListItem;
  items: LibraryItem[];
};

export default function ThreadDetailPage() {
  const params = useParams<{ id: string }>();
  const [data, setData] = useState<ThreadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`/api/library/threads/${params.id}`, { cache: "no-store" });
        if (!res.ok) {
          throw new Error("Failed to load thread");
        }
        setData((await res.json()) as ThreadResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    }

    void load();
  }, [params.id]);

  if (error) {
    return <p className="error">{error}</p>;
  }

  if (!data) {
    return <p>Loading thread...</p>;
  }

  return (
    <section className="panel">
      <p>
        <Link href="/app/library">? Back to library</Link>
      </p>
      <h2>{data.thread.title}</h2>
      {data.thread.is_partial && <p className="warning">This capture is marked partial.</p>}
      <ul>
        {data.items.map((item) => (
          <li key={item.id} className="tweet-card">
            <div>
              <a href={item.url} target="_blank" rel="noreferrer">
                @{item.author_handle}
              </a>
            </div>
            <p>{item.text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}


