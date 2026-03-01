import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { LibraryItem } from "@/lib/types";

type ItemsCardProps = {
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

export function ItemsCard({ items }: ItemsCardProps) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Latest Saved Tweets</CardTitle>
        <CardDescription>Recent tweet captures available for retrieval and chat.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.length === 0 ? (
          <p className="text-sm text-slate-600">No tweets saved yet.</p>
        ) : (
          items.slice(0, 20).map((item, index) => (
            <div key={item.id} className="space-y-3">
              {index > 0 && <Separator />}
              <article className="space-y-2">
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
                <p className="line-clamp-3 text-sm text-slate-700">{item.text}</p>
              </article>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
