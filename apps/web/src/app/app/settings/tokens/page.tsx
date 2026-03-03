"use client";

import { FormEvent, useEffect, useState } from "react";

import { TokenCreateForm } from "@/components/tokens/token-create-form";
import { TokenList } from "@/components/tokens/token-list";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { TokenListItem } from "@/lib/types";

type CreatedToken = {
  id: string;
  name: string;
  token: string;
  token_fingerprint: string;
  created_at: string;
  expires_at: string | null;
};

export default function TokenSettingsPage() {
  const [tokens, setTokens] = useState<TokenListItem[]>([]);
  const [name, setName] = useState("Extension PAT");
  const [expiresInDays, setExpiresInDays] = useState(90);
  const [created, setCreated] = useState<CreatedToken | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [revokingTokenId, setRevokingTokenId] = useState<string | null>(null);

  async function loadTokens() {
    const res = await fetch("/api/tokens", { cache: "no-store" });
    if (!res.ok) {
      throw new Error("Failed to load tokens");
    }

    setTokens((await res.json()) as TokenListItem[]);
  }

  useEffect(() => {
    void loadTokens().catch((err) => setError(err instanceof Error ? err.message : "Unknown error"));
  }, []);

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setCreating(true);

    try {
      const res = await fetch("/api/tokens", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name, expires_in_days: expiresInDays }),
      });

      if (!res.ok) {
        const maybeJson = await res.json().catch(() => ({}));
        throw new Error(maybeJson?.detail || "Failed to create token");
      }

      const payload = (await res.json()) as CreatedToken;
      setCreated(payload);
      await loadTokens();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setCreating(false);
    }
  }

  async function onRevoke(tokenId: string) {
    setError(null);
    setRevokingTokenId(tokenId);

    try {
      const res = await fetch(`/api/tokens/${tokenId}`, { method: "DELETE" });
      if (!res.ok) {
        const maybeJson = await res.json().catch(() => ({}));
        throw new Error(maybeJson?.detail || "Failed to revoke token");
      }

      await loadTokens();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setRevokingTokenId(null);
    }
  }

  return (
    <section className="space-y-6">
      <PageHeader
        title="API Tokens"
        description="Generate and manage personal access tokens used by the browser extension."
      />

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Token operation failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {created ? (
        <Alert variant="warning">
          <AlertTitle>Copy token now</AlertTitle>
          <AlertDescription>
            This is the only time the plaintext token is shown.
            <code className="mt-2 block break-all rounded-md border border-amber-200 bg-amber-100/70 p-2 text-xs text-amber-900">
              {created.token}
            </code>
            {created.expires_at ? (
              <p className="mt-2 text-xs text-amber-900">
                Expires: {new Date(created.expires_at).toLocaleString()}
              </p>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Create New Token</CardTitle>
          <CardDescription>
            Use one token per extension installation, set an expiry window, and rotate/revoke as needed.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <TokenCreateForm
            name={name}
            expiresInDays={expiresInDays}
            loading={creating}
            onNameChange={setName}
            onExpiresInDaysChange={setExpiresInDays}
            onSubmit={onCreate}
          />
        </CardContent>
      </Card>

      <TokenList tokens={tokens} revokingTokenId={revokingTokenId} onRevoke={onRevoke} />
    </section>
  );
}
