"use client";

import { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type TokenCreateFormProps = {
  name: string;
  expiresInDays: number;
  loading: boolean;
  onNameChange: (value: string) => void;
  onExpiresInDaysChange: (value: number) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function TokenCreateForm({
  name,
  expiresInDays,
  loading,
  onNameChange,
  onExpiresInDaysChange,
  onSubmit,
}: TokenCreateFormProps) {
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div className="space-y-1">
        <label htmlFor="token-name-input" className="text-sm font-medium text-slate-700">
          Token name
        </label>
        <Input
          id="token-name-input"
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          placeholder="Extension PAT"
          className="sm:max-w-sm"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="token-expiry-input" className="text-sm font-medium text-slate-700">
          Expiry window (days)
        </label>
        <Input
          id="token-expiry-input"
          value={expiresInDays}
          min={1}
          max={365}
          type="number"
          onChange={(event) => onExpiresInDaysChange(Number(event.target.value) || 1)}
          placeholder="90"
          className="sm:max-w-40"
        />
      </div>
      <Button type="submit" disabled={loading || !name.trim()}>
        {loading ? "Generating..." : "Generate token"}
      </Button>
    </form>
  );
}
