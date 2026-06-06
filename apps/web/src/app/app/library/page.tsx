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

const PAGE_SIZE = 50;

function buildLibraryParams({
  offset,
  activeFilter,
  activeAuthorFilter,
  searchQuery,
}: {
  offset: number;
  activeFilter: LibraryFolderFilter;
  activeAuthorFilter: string;
  searchQuery: string;
}) {
  const params = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String(offset),
  });

  if (activeFilter === "unassigned") {
    params.set("unassigned", "true");
  } else if (activeFilter !== "all") {
    params.set("folder_id", activeFilter);
  }

  if (activeAuthorFilter !== "all") {
    params.set("author_handle", activeAuthorFilter);
  }

  const cleanedSearch = searchQuery.trim();
  if (cleanedSearch) {
    params.set("q", cleanedSearch);
  }

  return params;
}

export default function LibraryPage() {
  const [threads, setThreads] = useState<LibraryThreadListItem[]>([]);
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [activeFilter, setActiveFilter] = useState<LibraryFolderFilter>("all");
  const [activeAuthorFilter, setActiveAuthorFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMoreThreads, setLoadingMoreThreads] = useState(false);
  const [loadingMoreItems, setLoadingMoreItems] = useState(false);
  const [hasMoreThreads, setHasMoreThreads] = useState(false);
  const [hasMoreItems, setHasMoreItems] = useState(false);
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

  const reloadFolders = useCallback(async () => {
    const foldersRes = await fetch("/api/library/folders", { cache: "no-store" });
    if (!foldersRes.ok) {
      throw new Error("Failed to load folders");
    }

    setFolders((await foldersRes.json()) as Folder[]);
  }, []);

  const fetchThreadsPage = useCallback(
    async (offset: number) => {
      const params = buildLibraryParams({
        offset,
        activeFilter,
        activeAuthorFilter,
        searchQuery: debouncedSearchQuery,
      });
      const res = await fetch(`/api/library/threads?${params.toString()}`, { cache: "no-store" });
      if (!res.ok) {
        throw new Error("Failed to load threads");
      }
      return (await res.json()) as LibraryThreadListItem[];
    },
    [activeAuthorFilter, activeFilter, debouncedSearchQuery],
  );

  const fetchItemsPage = useCallback(
    async (offset: number) => {
      const params = buildLibraryParams({
        offset,
        activeFilter,
        activeAuthorFilter,
        searchQuery: debouncedSearchQuery,
      });
      const res = await fetch(`/api/library/items?${params.toString()}`, { cache: "no-store" });
      if (!res.ok) {
        throw new Error("Failed to load items");
      }
      return (await res.json()) as LibraryItem[];
    },
    [activeAuthorFilter, activeFilter, debouncedSearchQuery],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [threadsJson, itemsJson] = await Promise.all([fetchThreadsPage(0), fetchItemsPage(0)]);
        setThreads(threadsJson);
        setItems(itemsJson);
        setHasMoreThreads(threadsJson.length === PAGE_SIZE);
        setHasMoreItems(itemsJson.length === PAGE_SIZE);
        await reloadFolders();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [fetchItemsPage, fetchThreadsPage, reloadFolders]);

  function onResetFilters() {
    setActiveFilter("all");
    setActiveAuthorFilter("all");
    setSearchQuery("");
  }

  async function onLoadMoreThreads() {
    setError(null);
    setLoadingMoreThreads(true);
    try {
      const next = await fetchThreadsPage(threads.length);
      setThreads((previous) => [...previous, ...next]);
      setHasMoreThreads(next.length === PAGE_SIZE);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoadingMoreThreads(false);
    }
  }

  async function onLoadMoreItems() {
    setError(null);
    setLoadingMoreItems(true);
    try {
      const next = await fetchItemsPage(items.length);
      setItems((previous) => [...previous, ...next]);
      setHasMoreItems(next.length === PAGE_SIZE);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoadingMoreItems(false);
    }
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
          threads={threads}
          folders={folders}
          assigningThreadId={assigningThreadId}
          hasMore={hasMoreThreads}
          loadingMore={loadingMoreThreads}
          onAssignFolder={onAssignThreadFolder}
          onLoadMore={onLoadMoreThreads}
        />
        <ItemsCard
          items={items}
          folders={folders}
          assigningItemId={assigningItemId}
          hasMore={hasMoreItems}
          loadingMore={loadingMoreItems}
          onAssignFolder={onAssignItemFolder}
          onLoadMore={onLoadMoreItems}
        />
      </div>
    </section>
  );
}
