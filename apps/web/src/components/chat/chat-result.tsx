import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { ChatSource } from "@/lib/types";

type ChatResultProps = {
  answerText: string;
  sources: ChatSource[];
};

export function ChatResult({ answerText, sources }: ChatResultProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Response</CardTitle>
        <CardDescription>Grounded output with source citations.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <article className="space-y-2">
          <h3 className="text-sm font-medium text-slate-800">Answer</h3>
          <pre className="overflow-x-auto rounded-md border border-slate-200 bg-slate-50 p-4 text-sm whitespace-pre-wrap text-slate-800">
            {answerText}
          </pre>
        </article>

        <article className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-medium text-slate-800">Sources Used</h3>
            <Badge variant="outline">{sources.length}</Badge>
          </div>
          {sources.length === 0 ? (
            <Alert variant="warning">
              <AlertTitle>No citations returned</AlertTitle>
              <AlertDescription>The model response did not include source citations.</AlertDescription>
            </Alert>
          ) : (
            sources.map((source, index) => (
              <div key={`${source.tweet_url}-${index}`} className="space-y-2">
                {index > 0 ? <Separator /> : null}
                <a
                  href={source.tweet_url}
                  target="_blank"
                  rel="noreferrer"
                  className="break-all text-sm font-medium text-emerald-700 hover:text-emerald-800"
                >
                  {source.tweet_url}
                </a>
                <p className="text-sm text-slate-700">{source.snippet}</p>
              </div>
            ))
          )}
        </article>
      </CardContent>
    </Card>
  );
}
