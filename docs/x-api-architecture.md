# Official X API Architecture

## Product Position

The default product name is **Investor Research Copilot** and can be changed with
`NEXT_PUBLIC_PRODUCT_NAME` and `APP_NAME`. X is an integration, not part of the product name.

The supported flow is:

```text
Web dashboard / URL-only Chrome extension
             -> application API
             -> centralized XApiClient
             -> OAuth refresh / lookup / search / bookmarks / usage accounting
             -> current library records, chunks, embeddings, and immutable thread snapshots
```

The extension never calls X APIs, reads X page DOM, injects scripts, expands replies, or extracts X
Article bodies. It sends only an explicitly selected active post URL, optional local folder ID, and
save mode.

## Storage Boundaries

- `x_integrations`: one encrypted OAuth token set per application user.
- `x_oauth_states`: short-lived, hashed, single-use OAuth state and encrypted PKCE verifier.
- `x_api_usage`: per-operation requested and returned post counts.
- `x_bookmark_folder_mappings`: explicit X bookmark-folder to local-folder mapping.
- `x_items`: current content plus verification status.
- `x_thread_captures` and `x_thread_capture_items`: immutable historical snapshots.
- `chat_messages.cited_sources_json`: persisted historical citations.

All X API calls use the connected user's token. Queries and writes retain the existing `user_id`
tenant boundary, so protected content retrieved for one user is not exposed to another user.

## Ingestion

`POST /v1/sources/x` parses a post ID, retrieves it from the official API, normalizes only required
fields, and uses the shared ingestion path. Content changes update the current chunk and embedding.
`author_thread` searches by `conversation_id`, filters to the root author, orders chronologically,
and creates a new immutable capture. It is marked partial because search access, age, pagination,
deletions, and permissions can prevent complete reconstruction.

Full-body X Article capture is disabled. Article URLs are stored only as link-only `unsupported`
records, and legacy article records are marked `unsupported`.

The previous client-supplied `/v1/ingest/x` route is not mounted in normal runtime. It is available
only under `APP_ENV=test` for historical snapshot regression fixtures.

## Future Lifecycle

Verification status and API usage records provide a boundary for a future compliance lifecycle
without replacing ingestion or storage architecture. This phase intentionally does not propagate
deletions or modifications into historical snapshots, historical embeddings, or persisted citations.
