"use client";

import { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type TokenCreateFormProps = {
  name: string;
  loading: boolean;
  onNameChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function TokenCreateForm({ name, loading, onNameChange, onSubmit }: TokenCreateFormProps) {
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-2 sm:flex-row">
      <Input
        value={name}
        onChange={(event) => onNameChange(event.target.value)}
        placeholder="Token name"
        className="sm:max-w-sm"
      />
      <Button type="submit" disabled={loading || !name.trim()}>
        {loading ? "Generating..." : "Generate token"}
      </Button>
    </form>
  );
}
