"use client";

import { FormEvent, useEffect, useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { XIntegrationStatus } from "@/lib/types";

export default function XSettingsPage() {
  const [status, setStatus] = useState<XIntegrationStatus | null>(null);
  const [url, setUrl] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadStatus() {
    const response = await fetch("/api/integrations/x/status", { cache: "no-store" });
    if (response.ok) setStatus(await response.json());
  }

  useEffect(() => {
    let active = true;
    void fetch("/api/integrations/x/status", { cache: "no-store" }).then(async (response) => {
      if (active && response.ok) setStatus(await response.json());
    });
    return () => {
      active = false;
    };
  }, []);

  async function action(path: string, method = "POST", body?: object) {
    setBusy(true);
    setMessage("");
    const response = await fetch(path, {
      method,
      headers: body ? { "content-type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const payload = await response.json().catch(() => ({}));
    setBusy(false);
    if (!response.ok) {
      setMessage(payload?.detail?.message || payload?.detail || "Request failed.");
      return null;
    }
    await loadStatus();
    return payload;
  }

  async function connect() {
    const payload = await action("/api/integrations/x/authorize");
    if (payload?.authorization_url) window.location.assign(payload.authorization_url);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    const payload = await action("/api/sources/x", "POST", { url, folder_id: null, mode: "post" });
    if (payload) setMessage("Post saved through the official X API.");
  }

  return (
    <section className="space-y-6">
      <PageHeader title="X Integration" description="Connect X to sync bookmarks and save posts through the official X API." />
      {message ? <Alert><AlertTitle>Status</AlertTitle><AlertDescription>{message}</AlertDescription></Alert> : null}
      <Card>
        <CardHeader>
          <CardTitle>Connection</CardTitle>
          <CardDescription>Requested scopes: tweet.read, users.read, bookmark.read, offline.access.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge variant={status?.connected ? "secondary" : "outline"}>{status?.status || "loading"}</Badge>
            {status?.x_username ? <Badge variant="outline">@{status.x_username}</Badge> : null}
            {(status?.granted_scopes || []).map((scope) => <Badge key={scope} variant="outline">{scope}</Badge>)}
          </div>
          <p className="text-sm text-slate-600">
            Monthly post reads: {status?.monthly_post_reads ?? 0} / {status?.monthly_post_read_budget ?? 0}
          </p>
          <div className="flex flex-wrap gap-2">
            {!status?.connected ? <Button disabled={busy} onClick={connect}>Connect X</Button> : null}
            {status?.connected ? <Button disabled={busy} onClick={() => void action("/api/integrations/x/bookmarks/sync")}>Sync bookmarks</Button> : null}
            {status?.connected ? <Button variant="outline" disabled={busy} onClick={() => void action("/api/integrations/x", "DELETE")}>Disconnect X</Button> : null}
          </div>
          {status?.last_bookmark_sync_at ? <p className="text-sm">Last sync: {new Date(status.last_bookmark_sync_at).toLocaleString()}</p> : null}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Save by URL</CardTitle><CardDescription>Full X Article bodies are unsupported. Thread reconstruction is best effort.</CardDescription></CardHeader>
        <CardContent>
          <form className="flex gap-2" onSubmit={save}>
            <Input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://x.com/user/status/123" />
            <Button disabled={busy || !status?.connected}>Save</Button>
          </form>
        </CardContent>
      </Card>
      <Alert>
        <AlertTitle>Historical retention phase</AlertTitle>
        <AlertDescription>
          Source revalidation may mark current content unavailable. Historical snapshots and persisted chat citations are intentionally preserved during this phase.
        </AlertDescription>
      </Alert>
    </section>
  );
}
