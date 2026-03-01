export type TokenListItem = {
  id: string;
  name: string;
  token_fingerprint: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
};

export type LibraryThreadListItem = {
  id: string;
  root_tweet_id: string | null;
  root_url: string | null;
  title: string;
  captured_at: string;
  capture_version: number;
  is_partial: boolean;
  item_count: number;
  author_handles: string[];
  folder_id: string | null;
  folder_name: string | null;
};

export type LibraryItem = {
  id: string;
  tweet_id: string;
  url: string;
  author_handle: string;
  author_name: string | null;
  created_at: string | null;
  captured_at: string;
  text: string;
  folder_id: string | null;
  folder_name: string | null;
};

export type Folder = {
  id: string;
  name: string;
  created_at: string;
  item_count: number;
  thread_count: number;
};

export type ChatSource = {
  tweet_url: string;
  tweet_id: string | null;
  author_handle: string | null;
  created_at: string | null;
  snippet: string;
};
