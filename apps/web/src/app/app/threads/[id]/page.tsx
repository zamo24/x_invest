"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import type { LibraryThreadListItem, ThreadCaptureItem, ThreadCaptureSummary } from "@/lib/types";

type ThreadResponse = {
  thread: LibraryThreadListItem;
  selected_capture: ThreadCaptureSummary;
  captures: ThreadCaptureSummary[];
  items: ThreadCaptureItem[];
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
  const [selectedVersion, setSelectedVersion] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const query = selectedVersion ? `?version=${encodeURIComponent(selectedVersion)}` : "";
        const res = await fetch(`/api/library/threads/${params.id}${query}`, { cache: "no-store" });
        if (!res.ok) {
          throw new Error("Failed to load thread");
        }

        setData((await res.json()) as ThreadResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    }

    void load();
  }, [params.id, selectedVersion]);

  if (error) {
    return (
      <section className="space-y-6">
        <PageHeader title="Thread" description="Inspect all posts captured for a specific thread snapshot." />
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
        <PageHeader title="Thread" description="Inspect all posts captured for a specific thread snapshot." />
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
        description="Inspect all posts captured for this thread snapshot."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link href="/app/library">Back to library</Link>
          </Button>
        }
      />

      {data.selected_capture.is_partial ? (
        <Alert variant="warning">
          <AlertTitle>Partial capture</AlertTitle>
          <AlertDescription>
            This thread snapshot is marked partial and may not include every reply.
            {data.selected_capture.partial_reason ? ` ${data.selected_capture.partial_reason}` : ""}
          </AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Thread Posts</CardTitle>
              <CardDescription>
                {data.items.length} saved posts in capture v{data.selected_capture.capture_version} from{" "}
                {formatDate(data.selected_capture.captured_at)}.
              </CardDescription>
            </div>
            <div className="min-w-48">
              <Select value={String(data.selected_capture.capture_version)} onChange={(event) => setSelectedVersion(event.target.value)}>
                {data.captures.map((capture) => (
                  <option key={capture.id} value={capture.capture_version}>
                    v{capture.capture_version} · {capture.item_count} items
                    {capture.is_partial ? " · partial" : ""}
                  </option>
                ))}
              </Select>
            </div>
          </div>
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
