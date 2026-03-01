import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { LibraryThreadListItem } from "@/lib/types";

type ThreadsCardProps = {
  threads: LibraryThreadListItem[];
};

export function ThreadsCard({ threads }: ThreadsCardProps) {
  return (
    <Card className="flex h-full max-h-[70vh] flex-col">
      <CardHeader>
        <CardTitle>Saved Threads</CardTitle>
        <CardDescription>Thread captures from X with version history.</CardDescription>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {threads.length === 0 ? (
          <p className="text-sm text-slate-600">No threads yet. Use the extension to save a thread from X.</p>
        ) : (
          threads.map((thread, index) => (
            <div key={thread.id} className="space-y-3">
              {index > 0 && <Separator />}
              <div className="space-y-2">
                <Link href={`/app/threads/${thread.id}`} className="font-medium text-slate-900 hover:text-emerald-700">
                  {thread.title}
                </Link>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">v{thread.capture_version}</Badge>
                  <Badge variant="secondary">{thread.item_count} items</Badge>
                  {thread.is_partial && <Badge variant="destructive">Partial capture</Badge>}
                </div>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
