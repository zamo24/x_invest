import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { TokenListItem } from "@/lib/types";

type TokenListProps = {
  tokens: TokenListItem[];
  referenceTime: number | null;
  revokingTokenId: string | null;
  onRevoke: (tokenId: string) => void;
};

function formatDate(value: string | null) {
  if (!value) {
    return "Never";
  }

  const asDate = new Date(value);
  if (Number.isNaN(asDate.getTime())) {
    return "Unknown";
  }

  return asDate.toLocaleString();
}

export function TokenList({ tokens, referenceTime, revokingTokenId, onRevoke }: TokenListProps) {
  const now = referenceTime ?? 0;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Issued Tokens</CardTitle>
        <CardDescription>Manage extension access, token expiry, and revoke credentials when needed.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {tokens.length === 0 ? (
          <p className="text-sm text-slate-600">No API tokens have been created yet.</p>
        ) : (
          tokens.map((token, index) => (
            <div key={token.id} className="space-y-3">
              {index > 0 ? <Separator /> : null}
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="space-y-1">
                  <p className="font-medium text-slate-900">{token.name}</p>
                  <p className="text-xs text-slate-500">{token.token_fingerprint}</p>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                    <span>Created: {formatDate(token.created_at)}</span>
                    <span>Last used: {formatDate(token.last_used_at)}</span>
                    <span>Expires: {formatDate(token.expires_at)}</span>
                  </div>
                  <Badge
                    variant={
                      token.revoked_at
                        ? "secondary"
                        : token.expires_at && new Date(token.expires_at).getTime() <= now
                          ? "warning"
                          : "outline"
                    }
                  >
                    {token.revoked_at
                      ? "Revoked"
                      : token.expires_at && new Date(token.expires_at).getTime() <= now
                        ? "Expired"
                        : "Active"}
                  </Badge>
                </div>
                {!token.revoked_at && !(token.expires_at && new Date(token.expires_at).getTime() <= now) ? (
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    disabled={revokingTokenId === token.id}
                    onClick={() => onRevoke(token.id)}
                  >
                    {revokingTokenId === token.id ? "Revoking..." : "Revoke"}
                  </Button>
                ) : null}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
