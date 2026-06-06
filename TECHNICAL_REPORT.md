# Technical Report: X Investor Copilot Codebase

This report reflects the current repository state at:
`C:\Users\zacka\x_investor_copilot`

Primary references:
- `README.md`
- `docker-compose.yml`
- `infra/docker-compose.yml`
- `apps/api/app`
- `apps/web/src`
- `apps/extension`

## 1. System Overview

This monorepo implements a B2C "save from X + chat over saved corpus" MVP with three runtime components:

1. `apps/api` - FastAPI, SQLAlchemy, Alembic, Postgres, and pgvector.
2. `apps/web` - Next.js App Router dashboard with Clerk auth and API proxy routes.
3. `apps/extension` - Chrome Manifest V3 extension for X capture and side-panel chat.

The architecture remains deliberately compact:

- Postgres is the system of record and vector store.
- Ingestion, chunking, embedding, and DB writes are synchronous.
- Extension authentication uses PATs.
- Web authentication uses Clerk session JWTs forwarded to the API.
- The API verifies Clerk JWTs directly with Clerk JWKS.

## 2. Core Design Decisions

### Separate Auth Planes

- Extension requests use PATs (`xic_pat_...`) stored as HMAC-SHA256 hashes with `TOKEN_PEPPER`.
- Web requests use Clerk session JWTs, verified in `apps/api/app/core/clerk_jwt.py`.
- Shared user-owned APIs accept either auth type through `get_any_authenticated_user`.

This keeps extension setup simple while avoiding the old header-trust shortcut for web identity.

### Postgres And pgvector

The database stores users, PATs, folders, X items, X threads, chunks, model settings, and chat history. Vector retrieval uses pgvector cosine distance over `chunks.embedding`.

### Local Defaults With Hosted Model Paths

The default local dev path uses deterministic local embeddings and a local rule-based answer builder:

- `EMBEDDING_MODEL=local-hash-v1`
- `CHAT_MODEL=local-grounded-v1`

Hosted OpenAI paths are implemented for embeddings and chat completions when non-local models and keys are configured. Per-user BYOK OpenAI keys are encrypted before storage.

### DOM-Only X Capture

The extension only captures user-visible DOM content after explicit user action. It does not crawl, intercept traffic, or run background scraping.

## 3. Runtime Topology

Top-level workspace:

- `package.json`
- `pnpm-workspace.yaml`

Compose files:

- `docker-compose.yml`
- `infra/docker-compose.yml`

Runtime graph:

1. `db` starts `pgvector/pgvector:pg16`.
2. `api` waits for DB health, runs Alembic migrations, then starts Uvicorn.
3. `web` starts Next.js dev mode and proxies dashboard API calls to `api`.
4. The browser extension calls `api` directly with a PAT.

## 4. Backend

Primary files:

- `apps/api/app/main.py`
- `apps/api/app/api/deps.py`
- `apps/api/app/api/routes/*.py`
- `apps/api/app/services/*.py`
- `apps/api/app/db/models.py`

Implemented API surface:

- `GET /health`
- `POST /v1/tokens`
- `GET /v1/tokens`
- `DELETE /v1/tokens/{id}`
- `POST /v1/ingest/x`
- `POST /v1/chat`
- `GET /v1/chat/threads`
- `GET /v1/chat/threads/{id}`
- `PATCH /v1/chat/threads/{id}`
- `DELETE /v1/chat/threads/{id}`
- `GET /v1/model-settings`
- `PUT /v1/model-settings`
- `GET /v1/library/items`
- `GET /v1/library/threads`
- `GET /v1/library/threads/{id}`
- `GET /v1/library/folders`
- `POST /v1/library/folders`
- `DELETE /v1/library/folders/{id}`
- `PATCH /v1/library/items/{id}/folder`
- `PATCH /v1/library/threads/{id}/folder`

## 5. Database Design

Current model set:

- `users`
- `api_tokens`
- `user_model_settings`
- `x_folders`
- `x_items`
- `x_threads`
- `x_thread_items`
- `chunks`
- `chat_threads`
- `chat_messages`

Migration sequence:

1. Initial users/PAT/X item/thread/chunk schema.
2. Thread dedupe/versioning support.
3. Folder organization.
4. User model settings and BYOK metadata.
5. Reasoning effort.
6. API token expiry.
7. Persisted chat threads and messages.

## 6. Ingest And Retrieval

`POST /v1/ingest/x` supports:

- Single tweet capture.
- Thread capture with recapture versioning.
- X article capture with long-content chunking.
- Optional folder assignment.

The API creates `x_item` chunks for tweets/articles and `x_thread` macro chunks for threads. Article chunks are split into multiple body chunks for long-form content.

Retrieval:

- Embeds the query.
- Searches `chunks` with pgvector cosine distance.
- Oversamples candidates before metadata filtering.
- Reranks filtered candidates with vector similarity, lexical overlap, and recency signals.
- Supports author/date/folder filters and single saved-thread scope.

## 7. Chat Generation

Chat requests create or continue persisted chat threads. The API stores both user and assistant messages, including cited sources and model execution metadata.

Generation modes:

- Local mode returns a deterministic grounded answer from retrieved snippets.
- Hosted/BYOK mode calls OpenAI chat completions.

The OpenAI path asks for strict JSON sections, parses the response, validates citations against retrieved source URLs, and relabels unsupported claims as `Unknown / Speculation`.

## 8. Web App

Primary files:

- `apps/web/src/proxy.ts`
- `apps/web/src/lib/server-api.ts`
- `apps/web/src/app/app/*`
- `apps/web/src/app/api/*`

Current dashboard routes:

- `/`
- `/app/library`
- `/app/chat`
- `/app/settings/models`
- `/app/settings/tokens`
- `/app/threads/[id]`
- `/sign-in/[[...sign-in]]`
- `/sign-up/[[...sign-up]]`

Dashboard capabilities:

- Library browsing.
- Server-backed library search, author filtering, folder filtering, and paged load-more results.
- Folder create/delete and item/thread assignment.
- API token create/revoke with expiry display.
- Hosted/BYOK model settings.
- Persisted chat thread selection, rename, delete, pagination, and message history.

## 9. Extension

Primary files:

- `apps/extension/manifest.json`
- `apps/extension/capture-core.js`
- `apps/extension/content-script.js`
- `apps/extension/background.js`
- `apps/extension/options.js`
- `apps/extension/sidepanel.js`

Capabilities:

- Configure PAT and API base URL.
- Inject X toolbar with folder selector.
- Save tweet, thread, or article.
- Open side panel.
- Ask chat questions and continue saved chat threads.

Known limitation: capture quality depends on X DOM structure and currently rendered/expanded content.

## 10. Security And Operations

Implemented hardening:

- API verifies Clerk JWT issuer, signature, optional audience, and leeway.
- PATs are random, prefix-validated, HMAC-hashed, expirable, and revocable.
- API rejects wildcard CORS origins when credentials are enabled.
- API emits request IDs and structured access/error logs.
- BYOK API keys are encrypted with Fernet-compatible key derivation.
- In-process fixed-window rate limits protect chat, ingest, and token routes.

Remaining production considerations:

- Configure real Clerk issuer/JWKS/audience values before exposing the API.
- Use a strong `TOKEN_PEPPER` and `BYOK_ENCRYPTION_KEY`.
- Restrict CORS origins and extension IDs to production values.
- Tune rate limits/quotas for production traffic patterns.
- Use a distributed rate limiter or API gateway when running more than one API instance.
- Consider storing extension PATs in `chrome.storage.local` or documenting sync-storage tradeoffs.

## 11. Tests And Validation

Current automated coverage:

- API pytest integration tests for auth, observability, token expiry, article ingest, folders, model settings, grounded chat validation, and chat threads.
- Extension Vitest/jsdom tests for tweet and article extraction.
- Web Playwright smoke test for the landing page.
- Web lint and production build checks.
- GitHub Actions secret scan.

Useful commands:

```bash
docker compose run --rm --build -e EMBEDDING_MODEL=local-hash-v1 -e CHAT_MODEL=local-grounded-v1 api python -m pytest -q
pnpm -C apps/extension test
pnpm -C apps/web lint
pnpm -C apps/web build
pnpm -C apps/web test:e2e:list
```

## 12. Remaining Engineering Priorities

1. Broaden web e2e coverage for dashboard flows.
2. Run API pytest in CI with Postgres/pgvector.
3. Add distributed production rate limits and tighter operational controls.
4. Add retrieval evaluation fixtures and tune hybrid scoring against them.
5. Add total counts and cursor pagination for large library datasets.
6. Improve extension side-panel scope/folder controls.
7. Add observability metrics and runbook-level deployment docs.
