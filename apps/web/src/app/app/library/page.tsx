"use client";

import { useEffect, useState } from "react";

import { ItemsCard } from "@/components/library/items-card";
import { LibraryLoadingState } from "@/components/library/library-loading";
import { ThreadsCard } from "@/components/library/threads-card";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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

    void load();
  }, []);

  if (loading) {
    return (
      <section className="space-y-6">
        <PageHeader
          title="Library"
          description="Review saved thread captures and recent tweets ingested from your extension."
        />
        <LibraryLoadingState />
      </section>
    );
  }

  if (error) {
    return (
      <section className="space-y-6">
        <PageHeader
          title="Library"
          description="Review saved thread captures and recent tweets ingested from your extension."
        />
        <Alert variant="destructive">
          <AlertTitle>Failed to load library</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <PageHeader
        title="Library"
        description="Review saved thread captures and recent tweets ingested from your extension."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <ThreadsCard threads={threads} />
        <ItemsCard items={items} />
      </div>
    </section>
  );
}
