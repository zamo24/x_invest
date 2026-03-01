"use client";

import { FormEvent, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import type { Folder } from "@/lib/types";

export type LibraryFolderFilter = "all" | "unassigned" | string;

type FolderControlsProps = {
  folders: Folder[];
  activeFilter: LibraryFolderFilter;
  activeAuthorFilter: string;
  authorHandles: string[];
  searchQuery: string;
  creating: boolean;
  deletingFolderId: string | null;
  onFilterChange: (value: LibraryFolderFilter) => void;
  onAuthorFilterChange: (value: string) => void;
  onSearchQueryChange: (value: string) => void;
  onResetFilters: () => void;
  onCreateFolder: (name: string) => void;
  onDeleteFolder: (folderId: string) => void;
};

export function FolderControls({
  folders,
  activeFilter,
  activeAuthorFilter,
  authorHandles,
  searchQuery,
  creating,
  deletingFolderId,
  onFilterChange,
  onAuthorFilterChange,
  onSearchQueryChange,
  onResetFilters,
  onCreateFolder,
  onDeleteFolder,
}: FolderControlsProps) {
  const [newFolderName, setNewFolderName] = useState("");
  const hasActiveFilters = activeFilter !== "all" || activeAuthorFilter !== "all" || searchQuery.trim().length > 0;

  function onCreateSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = newFolderName.trim();
    if (!trimmed) {
      return;
    }

    onCreateFolder(trimmed);
    setNewFolderName("");
  }

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="space-y-1">
        <p className="text-sm font-medium text-slate-900">Manage topic folders</p>
        <p className="text-xs text-slate-600">Group your saved tweets and threads by thesis topic.</p>
      </div>

      <p className="text-right text-xs text-slate-500">{folders.length} folders</p>

      <form onSubmit={onCreateSubmit} className="flex flex-col gap-2 sm:flex-row">
        <Input
          value={newFolderName}
          onChange={(event) => setNewFolderName(event.target.value)}
          placeholder="New folder name (e.g. HBM, Photonics)"
          maxLength={120}
        />
        <Button type="submit" disabled={creating || !newFolderName.trim()}>
          {creating ? "Creating..." : "Create folder"}
        </Button>
      </form>

      {folders.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          {folders.map((folder) => (
            <Badge key={folder.id} variant="outline" className="inline-flex items-center gap-2 py-1">
              <span>{folder.name}</span>
              <span className="text-[10px] text-slate-500">{folder.thread_count + folder.item_count}</span>
              <button
                type="button"
                className="text-xs text-rose-700 hover:text-rose-800"
                disabled={deletingFolderId === folder.id}
                onClick={() => onDeleteFolder(folder.id)}
              >
                {deletingFolderId === folder.id ? "..." : "x"}
              </button>
            </Badge>
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-500">No folders yet.</p>
      )}

      <Separator />

      <div className="space-y-1">
        <p className="text-sm font-medium text-slate-900">Find saved content</p>
        <p className="text-xs text-slate-600">Search across threads and tweets, then narrow by folder or X user.</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
        <div className="space-y-1">
          <p className="text-xs font-medium text-slate-700">Search</p>
          <Input
            value={searchQuery}
            onChange={(event) => onSearchQueryChange(event.target.value)}
            placeholder="Search text, title, URL, author, tweet ID..."
          />
        </div>

        <div className="min-w-0 space-y-1">
          <p className="text-xs font-medium text-slate-700">Folder</p>
          <Select value={activeFilter} onChange={(event) => onFilterChange(event.target.value)}>
            <option value="all">All folders</option>
            <option value="unassigned">Unassigned only</option>
            {folders.map((folder) => (
              <option key={folder.id} value={folder.id}>
                {folder.name}
              </option>
            ))}
          </Select>
        </div>

        <div className="min-w-0 space-y-1">
          <p className="text-xs font-medium text-slate-700">X user</p>
          <Select value={activeAuthorFilter} onChange={(event) => onAuthorFilterChange(event.target.value)}>
            <option value="all">All users</option>
            {authorHandles.map((authorHandle) => (
              <option key={authorHandle} value={authorHandle}>
                @{authorHandle}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex items-end">
          <Button type="button" variant="outline" disabled={!hasActiveFilters} onClick={onResetFilters}>
            Clear
          </Button>
        </div>
      </div>
    </section>
  );
}
