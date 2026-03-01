"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import type { LibraryItem, LibraryThreadListItem } from "@/lib/types";

type ThreadResponse = {
  thread: LibraryThreadListItem;
  items: LibraryItem[];
};

function formatDate(value: string | null) {
  if (!value) {
    return "Unknown date";
  }

  const asDate = new Date(value);
  if (Number.isNaN(asDate.getTime())) {
    return "Unknown date";
  }

  return asDate.toLocaleString();
}

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
    return (
      <section className="space-y-6">
        <PageHeader title="Thread" description="Inspect all tweets captured for a specific thread snapshot." />
        <Alert variant="destructive">
          <AlertTitle>Failed to load thread</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="space-y-6">
        <PageHeader title="Thread" description="Inspect all tweets captured for a specific thread snapshot." />
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-1/3" />
            <Skeleton className="h-4 w-2/3" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </CardContent>
        </Card>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <PageHeader
        title={data.thread.title}
        description="Inspect all tweets captured for this thread snapshot."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link href="/app/library">Back to library</Link>
          </Button>
        }
      />

      {data.thread.is_partial ? (
        <Alert variant="warning">
          <AlertTitle>Partial capture</AlertTitle>
          <AlertDescription>This thread snapshot is marked partial and may not include every reply.</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Thread Tweets</CardTitle>
          <CardDescription>{data.items.length} saved tweets in this capture.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.items.map((item, index) => (
            <div key={item.id} className="space-y-3">
              {index > 0 ? <Separator /> : null}
              <article className="space-y-2 rounded-md border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-slate-900 hover:text-emerald-700"
                  >
                    @{item.author_handle}
                  </a>
                  <Badge variant="outline">{formatDate(item.created_at ?? item.captured_at)}</Badge>
                </div>
                <p className="text-sm text-slate-700 whitespace-pre-wrap">{item.text}</p>
              </article>
            </div>
          ))}
        </CardContent>
      </Card>
    </section>
  );
}
