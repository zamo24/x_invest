"use client";

import { FormEvent, useEffect, useState } from "react";

import type { TokenListItem } from "@/lib/types";

type CreatedToken = {
  id: string;
  name: string;
  token: string;
  token_fingerprint: string;
  created_at: string;
};

export default function TokenSettingsPage() {
  const [tokens, setTokens] = useState<TokenListItem[]>([]);
  const [name, setName] = useState("Extension PAT");
  const [created, setCreated] = useState<CreatedToken | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);

    try {
      const res = await fetch("/api/tokens", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) {
        throw new Error("Failed to create token");
      }
      const payload = (await res.json()) as CreatedToken;
      setCreated(payload);
      await loadTokens();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function onRevoke(tokenId: string) {
    setError(null);
    try {
      const res = await fetch(`/api/tokens/${tokenId}`, { method: "DELETE" });
      if (!res.ok) {
        throw new Error("Failed to revoke token");
      }
      await loadTokens();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  return (
    <section className="panel">
      <h2>API Tokens</h2>
      <p>Generate a PAT for the extension. The plaintext token is shown only once.</p>

      <form onSubmit={onCreate} className="token-form">
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Token name" />
        <button type="submit" className="primary">
          Generate token
        </button>
      </form>

      {created && (
        <div className="token-once">
          <h3>Copy now (shown once)</h3>
          <code>{created.token}</code>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      <ul>
        {tokens.map((token) => (
          <li key={token.id} className="list-row token-row">
            <div>
              <p>{token.name}</p>
              <p>{token.token_fingerprint}</p>
              <p>{token.revoked_at ? "Revoked" : "Active"}</p>
            </div>
            {!token.revoked_at && (
              <button type="button" className="danger" onClick={() => onRevoke(token.id)}>
                Revoke
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
