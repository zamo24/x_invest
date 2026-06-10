# Technical Report: Investor Research Copilot

## System Overview

The monorepo contains a FastAPI/PostgreSQL/pgvector API, Next.js/Clerk dashboard, and Chrome Manifest
V3 extension. PostgreSQL is the system of record and vector store. Application data is tenant-scoped
by `user_id`. Local deterministic embedding and chat modes remain supported.

## Official X API Integration

X content ingestion is server-side through a centralized typed client. The client handles encrypted
OAuth 2.0 PKCE credentials, refresh, single and batch post lookup, authenticated bookmarks, bookmark
folders, conversation search, normalized errors, and usage-budget enforcement.

The extension is URL-only. It has no X content scripts, broad X host permission, scripting permission,
DOM extraction, injected toolbar, reply automation, or X Article extraction. Explicit save actions
send only URL, optional folder ID, and `post` or `author_thread` mode.

## Data Model And Migration

Migration `20260610_0009_x_api_integration.py` adds:

- Per-user encrypted X integrations.
- Hashed, expiring, single-use OAuth state with encrypted PKCE verifier.
- X API usage-accounting records.
- X bookmark-folder to local-folder mappings.
- Current-source verification status, timestamps, and unavailable reason.

Legacy X records are marked pending verification. Legacy full-body X Article records are marked
unsupported. Existing folders, current content, chunks, embeddings, immutable thread captures, and
persisted chat citations are preserved.

## Ingestion And History

`POST /v1/sources/x` retrieves a post through the official X API and upserts current library content.
Current chunks and embeddings are regenerated only when normalized content changes.

Author-thread mode searches by `conversation_id`, filters to the root author, orders results
chronologically, and appends an immutable capture. Captures are marked partial when completeness
cannot be guaranteed. Full-body X Article capture is disabled.

Bookmark sync paginates and upserts through the same normalized ingestion service. It maps bookmark
folders without overwriting unrelated local folders and conservatively retains local sources removed
from X.

## Revalidation, Retrieval, And Chat

`python -m app.cli.revalidate_x` batches up to 100 current post IDs, refreshes changed current
content, marks unavailable sources, records verification outcomes, and preserves historical
snapshots and persisted citations. Retrieval prioritizes active verified content and the web library
labels unavailable or unverified sources.

Chat remains source-cited and tenant-scoped. Protected content retrieved with one user's token is not
made available to another user. The application does not train or fine-tune models using X content.

## Security And Operations

- Clerk JWTs and extension PATs remain separate authentication planes.
- PATs are HMAC-hashed and revocable.
- X tokens and PKCE verifiers are encrypted at rest.
- Only `tweet.read`, `users.read`, `bookmark.read`, and `offline.access` are requested.
- X credentials and API calls remain server-side.
- Per-operation usage records and configurable monthly/per-sync limits control cost.
- External API calls are mocked in automated tests.

## Compliance Boundary

This technical design is not a legal or X policy compliance guarantee. The current phase
intentionally preserves immutable historical X content and does not propagate deletions or
modifications through historical snapshots, embeddings, or persisted chat citations.

The product must not be represented as fully compliant with X policies until legal review and written
X approval confirm the retention model. Remaining approval gates and deferred lifecycle work are
documented in `docs/x-api-compliance.md`.
