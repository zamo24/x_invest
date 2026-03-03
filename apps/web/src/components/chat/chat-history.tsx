import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { ChatMessageItem } from "@/lib/types";

type ChatHistoryProps = {
  messages: ChatMessageItem[];
};

function formatDate(value: string) {
  const asDate = new Date(value);
  if (Number.isNaN(asDate.getTime())) {
    return "Unknown time";
  }
  return asDate.toLocaleString();
}

export function ChatHistory({ messages }: ChatHistoryProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Conversation History</CardTitle>
        <CardDescription>Follow-up prompts continue this saved thread.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {messages.length === 0 ? (
          <p className="text-sm text-slate-600">No messages yet. Ask your first question to start a thread.</p>
        ) : (
          messages.map((message, index) => (
            <div key={message.id} className="space-y-2">
              {index > 0 ? <Separator /> : null}
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{message.role}</p>
                <p className="text-xs text-slate-500">{formatDate(message.created_at)}</p>
              </div>
              <pre className="overflow-x-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-sm whitespace-pre-wrap text-slate-800">
                {message.message_text}
              </pre>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
