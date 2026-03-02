"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { FolderControls, type LibraryFolderFilter } from "@/components/library/folder-controls";
import { ItemsCard } from "@/components/library/items-card";
import { LibraryLoadingState } from "@/components/library/library-loading";
import { ThreadsCard } from "@/components/library/threads-card";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { Folder, LibraryItem, LibraryThreadListItem } from "@/lib/types";

type FolderAssignmentResponse = {
  id: string;
  folder_id: string | null;
  folder_name: string | null;
};

export default function LibraryPage() {
  const [threads, setThreads] = useState<LibraryThreadListItem[]>([]);
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [activeFilter, setActiveFilter] = useState<LibraryFolderFilter>("all");
  const [activeAuthorFilter, setActiveAuthorFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [deletingFolderId, setDeletingFolderId] = useState<string | null>(null);
  const [assigningItemId, setAssigningItemId] = useState<string | null>(null);
  const [assigningThreadId, setAssigningThreadId] = useState<string | null>(null);

  const authorHandles = useMemo(() => {
    const handles = new Set<string>();
    for (const item of items) {
      if (item.author_handle && item.author_handle !== "unknown") {
        handles.add(item.author_handle);
      }
    }
    for (const thread of threads) {
      for (const handle of thread.author_handles ?? []) {
        if (handle) {
          handles.add(handle);
        }
      }
    }
    return Array.from(handles).sort((a, b) => a.localeCompare(b));
  }, [items, threads]);

  const normalizedSearch = searchQuery.trim().toLowerCase();
  const searchTerms = useMemo(
    () => normalizedSearch.split(/\s+/).filter((term) => term.length > 0),
    [normalizedSearch],
  );

  const reloadFolders = useCallback(async () => {
    const foldersRes = await fetch("/api/library/folders", { cache: "no-store" });
    if (!foldersRes.ok) {
      throw new Error("Failed to load folders");
    }

    setFolders((await foldersRes.json()) as Folder[]);
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const [threadsRes, itemsRes] = await Promise.all([
          fetch("/api/library/threads", { cache: "no-store" }),
          fetch("/api/library/items", { cache: "no-store" }),
        ]);

        if (!threadsRes.ok || !itemsRes.ok) {
          throw new Error("Failed to load library");
        }

        const threadsJson = (await threadsRes.json()) as LibraryThreadListItem[];
        const itemsJson = (await itemsRes.json()) as LibraryItem[];

        setThreads(threadsJson);
        setItems(itemsJson);
        await reloadFolders();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [reloadFolders]);

  const filteredThreads = useMemo(() => {
    return threads.filter((thread) => {
      if (activeFilter === "unassigned" && thread.folder_id) {
        return false;
      }
      if (activeFilter !== "all" && activeFilter !== "unassigned" && thread.folder_id !== activeFilter) {
        return false;
      }
      if (activeAuthorFilter !== "all" && !(thread.author_handles ?? []).includes(activeAuthorFilter)) {
        return false;
      }
      if (searchTerms.length === 0) {
        return true;
      }

      const haystack = [
        thread.id,
        thread.root_tweet_id,
        thread.root_url,
        thread.title,
        thread.captured_at,
        thread.folder_name,
        ...(thread.author_handles ?? []),
      ]
        .filter((value): value is string => Boolean(value))
        .join(" ")
        .toLowerCase();

      return searchTerms.every((term) => haystack.includes(term));
    });
  }, [threads, activeFilter, activeAuthorFilter, searchTerms]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (activeFilter === "unassigned" && item.folder_id) {
        return false;
      }
      if (activeFilter !== "all" && activeFilter !== "unassigned" && item.folder_id !== activeFilter) {
        return false;
      }
      if (activeAuthorFilter !== "all" && item.author_handle !== activeAuthorFilter) {
        return false;
      }
      if (searchTerms.length === 0) {
        return true;
      }

      const haystack = [
        item.id,
        item.tweet_id,
        item.url,
        item.author_handle,
        item.author_name,
        item.created_at,
        item.captured_at,
        item.source_kind,
        item.title,
        item.text,
        item.folder_name,
      ]
        .filter((value): value is string => Boolean(value))
        .join(" ")
        .toLowerCase();

      return searchTerms.every((term) => haystack.includes(term));
    });
  }, [items, activeFilter, activeAuthorFilter, searchTerms]);

  function onResetFilters() {
    setActiveFilter("all");
    setActiveAuthorFilter("all");
    setSearchQuery("");
  }

  async function onCreateFolder(name: string) {
    setError(null);
    setCreatingFolder(true);
    try {
      const res = await fetch("/api/library/folders", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) {
        const maybeJson = await res.json().catch(() => ({}));
        throw new Error(maybeJson?.detail || "Failed to create folder");
      }

      const folder = (await res.json()) as Folder;
      setFolders((previous) => [...previous, folder].sort((a, b) => a.name.localeCompare(b.name)));
      await reloadFolders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setCreatingFolder(false);
    }
  }

  async function onDeleteFolder(folderId: string) {
    setError(null);
    setDeletingFolderId(folderId);

    try {
      const res = await fetch(`/api/library/folders/${folderId}`, { method: "DELETE" });
      if (!res.ok) {
        const maybeJson = await res.json().catch(() => ({}));
        throw new Error(maybeJson?.detail || "Failed to delete folder");
      }

      setFolders((previous) => previous.filter((folder) => folder.id !== folderId));
      setThreads((previous) =>
        previous.map((thread) => (thread.folder_id === folderId ? { ...thread, folder_id: null, folder_name: null } : thread)),
      );
      setItems((previous) =>
        previous.map((item) => (item.folder_id === folderId ? { ...item, folder_id: null, folder_name: null } : item)),
      );
      if (activeFilter === folderId) {
        setActiveFilter("all");
      }
      await reloadFolders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setDeletingFolderId(null);
    }
  }

  async function onAssignItemFolder(itemId: string, folderId: string | null) {
    setError(null);
    setAssigningItemId(itemId);

    try {
      const res = await fetch("/api/library/items/folder", {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ item_id: itemId, folder_id: folderId }),
      });
      if (!res.ok) {
        const maybeJson = await res.json().catch(() => ({}));
        throw new Error(maybeJson?.detail || "Failed to assign item folder");
      }

      const updated = (await res.json()) as FolderAssignmentResponse;
      setItems((previous) =>
        previous.map((item) =>
          item.id === updated.id
            ? {
                ...item,
                folder_id: updated.folder_id,
                folder_name: updated.folder_name,
              }
            : item,
        ),
      );
      await reloadFolders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setAssigningItemId(null);
    }
  }

  async function onAssignThreadFolder(threadId: string, folderId: string | null) {
    setError(null);
    setAssigningThreadId(threadId);

    try {
      const res = await fetch("/api/library/threads/folder", {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, folder_id: folderId }),
      });
      if (!res.ok) {
        const maybeJson = await res.json().catch(() => ({}));
        throw new Error(maybeJson?.detail || "Failed to assign thread folder");
      }

      const updated = (await res.json()) as FolderAssignmentResponse;
      setThreads((previous) =>
        previous.map((thread) =>
          thread.id === updated.id
            ? {
                ...thread,
                folder_id: updated.folder_id,
                folder_name: updated.folder_name,
              }
            : thread,
        ),
      );
      await reloadFolders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setAssigningThreadId(null);
    }
  }

  if (loading) {
    return (
      <section className="space-y-6">
        <PageHeader
          title="Library"
          description="Review saved thread captures and recent items ingested from your extension."
        />
        <LibraryLoadingState />
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <PageHeader
        title="Library"
        description="Review saved thread captures and recent items ingested from your extension."
      />

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Library operation failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <FolderControls
        folders={folders}
        activeFilter={activeFilter}
        activeAuthorFilter={activeAuthorFilter}
        authorHandles={authorHandles}
        searchQuery={searchQuery}
        creating={creatingFolder}
        deletingFolderId={deletingFolderId}
        onFilterChange={setActiveFilter}
        onAuthorFilterChange={setActiveAuthorFilter}
        onSearchQueryChange={setSearchQuery}
        onResetFilters={onResetFilters}
        onCreateFolder={onCreateFolder}
        onDeleteFolder={onDeleteFolder}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <ThreadsCard
          threads={filteredThreads}
          folders={folders}
          assigningThreadId={assigningThreadId}
          onAssignFolder={onAssignThreadFolder}
        />
        <ItemsCard
          items={filteredItems}
          folders={folders}
          assigningItemId={assigningItemId}
          onAssignFolder={onAssignItemFolder}
        />
      </div>
    </section>
  );
}
