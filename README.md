# X Investor Copilot (MVP)

Browser extension + web app that lets users save X (Twitter) tweets/threads/articles and chat over a personal, source-grounded RAG library with citations to exact source URLs.

## Monorepo Structure

- `apps/web` - Next.js App Router dashboard + Clerk auth + token management + library/chat UI
- `apps/api` - FastAPI + SQLAlchemy + Alembic + pgvector ingest/retrieval/chat APIs
- `apps/extension` - Manifest V3 extension (options PAT, content script save actions, side panel chat)
- `infra/docker-compose.yml` - Local dev compose stack
- `docs/architecture` - accepted architecture decisions and scaling strategy

## Prerequisites

- Docker + Docker Compose
- Node 20+
- pnpm 9+ (the workspace is pinned to `pnpm@9.0.0`)
- Python 3.11+ (optional for local non-docker API dev)
- Clerk account/app for web auth

## Environment Setup

1. Copy env template:

```bash
cp .env.example .env
```

2. Fill Clerk vars in `.env`:

- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`
- `CLERK_ISSUER` (e.g. `https://YOUR_INSTANCE.clerk.accounts.dev`)
- `CLERK_JWKS_URL` (usually `${CLERK_ISSUER}/.well-known/jwks.json`)
- `CLERK_AUDIENCE` (optional; set only if your Clerk JWT includes `aud`)
- `CLERK_JWT_LEEWAY_SECONDS` (optional; default `30`, helps avoid intermittent token clock-skew issues)
- `CLERK_JWT_TEMPLATE` (optional; set only if you configured a custom Clerk JWT template for backend auth)

3. Set `TOKEN_PEPPER` to a long random string.
   Optional token policy:
   - `PAT_DEFAULT_TTL_DAYS` (default `90`)
   - `PAT_MAX_TTL_DAYS` (default `365`)
   Optional in-process rate limits:
   - `RATE_LIMIT_ENABLED=true`
   - `RATE_LIMIT_WINDOW_SECONDS=60`
   - `RATE_LIMIT_CHAT_REQUESTS=30`
   - `RATE_LIMIT_INGEST_REQUESTS=60`
   - `RATE_LIMIT_TOKEN_REQUESTS=30`

4. For OpenAI-backed embeddings + chat (step 2), set:

- `OPENAI_API_KEY` (or `LLM_API_KEY`)
- `EMBEDDING_MODEL=text-embedding-3-small`
- `CHAT_MODEL=gpt-4o-mini`
- `EMBEDDING_DIM=256` (keeps compatibility with current pgvector schema)
- Optional: `OPENAI_BASE_URL`, `OPENAI_TIMEOUT_SECONDS`
- `BYOK_ENCRYPTION_KEY` (required if users will store BYOK API keys)
- `HOSTED_CHAT_PROVIDER=openai`
- `HOSTED_CHAT_MODELS=gpt-4o-mini,gpt-4.1-mini,gpt-5-mini,gpt-5.2`

Optional retrieval tuning:

- `RETRIEVAL_OVERSAMPLE_MULTIPLIER=6`
- `RETRIEVAL_MIN_CANDIDATES=30`
- `RETRIEVAL_LEXICAL_WEIGHT=0.18`
- `RETRIEVAL_RECENCY_WEIGHT=0.04`

5. CORS hardening defaults (can override if needed):

- `CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`
- `CORS_ALLOW_ORIGIN_REGEX=^chrome-extension://[a-z]{32}$`
- `CORS_EXTENSION_IDS=` (set exact published extension IDs in production)
- `CORS_ALLOW_METHODS=GET,POST,PUT,PATCH,DELETE,OPTIONS`
- `CORS_ALLOW_HEADERS=Authorization,Content-Type`
- `CORS_ALLOW_CREDENTIALS=true`
- Do not use `*` in `CORS_ALLOW_ORIGINS` when credentials are enabled.
- In production, set `APP_ENV=production`, clear `CORS_ALLOW_ORIGIN_REGEX`, and configure exact `CORS_EXTENSION_IDS`.

6. Observability defaults:

- `APP_VERSION=0.1.0`
- `LOG_LEVEL=INFO`
- API responses include `x-request-id` for tracing.
- Rate-limited responses return HTTP `429`, `retry-after`, and `x-ratelimit-*` headers.

## Run Locally (Docker)

From repo root:

```bash
docker compose up --build
```

Services:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Postgres: `localhost:55432`

`web` now runs in Next.js dev mode with bind-mounted source for hot reload. UI edits in `apps/web` should appear without restarting containers.
If you change dependencies (`package.json` / lockfile), restart the `web` service once.

If `web` fails to boot after switching compose versions, reset the web dependency volume once:

```bash
docker compose down
docker volume rm x_investor_copilot_web_node_modules
docker compose up -d --build web
```

`api` container runs migrations at startup:

```bash
alembic upgrade head
```

## Run With Infra Compose File

```bash
docker compose -f infra/docker-compose.yml up --build
```

## Automated Tests

API unit + integration tests:

```bash
docker compose run --rm --build -e EMBEDDING_MODEL=local-hash-v1 -e CHAT_MODEL=local-grounded-v1 api python -m pytest -q
```

Extension capture harness (jsdom + vitest):

```bash
pnpm -C apps/extension test
```

Web e2e test listing (Playwright):

```bash
pnpm -C apps/web test:e2e:list
```

Secret scan (GitHub Actions):

- `.github/workflows/secret-scan.yml` runs gitleaks on push/PR.

## API Endpoints (MVP)

- `POST /v1/tokens` (Bearer Clerk JWT) create PAT
- `GET /v1/tokens` list PATs
- `DELETE /v1/tokens/{id}` revoke PAT
- `POST /v1/ingest/x` (Bearer PAT) ingest tweet/thread/article capture
- `POST /v1/chat` (Bearer PAT or Bearer Clerk JWT) source-grounded chat
- `GET /v1/model-settings` (Bearer PAT or Bearer Clerk JWT) get hosted/BYOK model settings
- `PUT /v1/model-settings` update hosted/BYOK model settings (OpenAI BYOK in MVP, including `reasoning_effort` for GPT-5 models)
- `GET /v1/library/items?limit=&offset=&folder_id=&unassigned=&q=&author_handle=` (Bearer PAT or Bearer Clerk JWT)
- `GET /v1/library/threads?limit=&offset=&folder_id=&unassigned=&q=&author_handle=` (Bearer PAT or Bearer Clerk JWT)
- `GET /v1/library/threads/{id}?version=` get latest or historical immutable capture snapshot
- `GET /v1/library/folders` (Bearer PAT or Bearer Clerk JWT)
- `POST /v1/library/folders` create a topic folder
- `DELETE /v1/library/folders/{id}` delete folder (saved content remains, becomes unassigned)
- `PATCH /v1/library/items/{id}/folder` assign/unassign tweet folder
- `PATCH /v1/library/threads/{id}/folder` assign/unassign thread folder

## Curl Examples

### 1) Create token (web/Clerk context)

Best path: create/revoke tokens in the dashboard at `http://localhost:3000/app/settings/tokens`.

Direct API example (requires a valid Clerk session JWT):

```bash
curl -X POST http://localhost:8000/v1/tokens \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer CLERK_SESSION_JWT" \
  -d '{"name":"Extension PAT","expires_in_days":90}'
```

### 2) Ingest X payload (extension/PAT)

```bash
curl -X POST http://localhost:8000/v1/ingest/x \
  -H "Authorization: Bearer xic_pat_REPLACE_ME" \
  -H "Content-Type: application/json" \
  -d '{
    "capture_type": "thread",
    "page_url": "https://x.com/someuser/status/1234567890",
    "root_tweet_id": "1234567890",
    "root_tweet_url": "https://x.com/someuser/status/1234567890",
    "tweets": [
      {
        "tweet_id": "1234567890",
        "url": "https://x.com/someuser/status/1234567890",
        "author_handle": "someuser",
        "author_name": "Some User",
        "text": "HBM demand still outstrips supply.",
        "captured_at": "2026-02-27T01:00:00Z"
      }
    ],
    "captured_count": 1,
    "is_partial": false
  }'
```

Article ingest example:

```bash
curl -X POST http://localhost:8000/v1/ingest/x \
  -H "Authorization: Bearer xic_pat_REPLACE_ME" \
  -H "Content-Type: application/json" \
  -d '{
    "capture_type": "article",
    "page_url": "https://x.com/i/article/abc123",
    "article": {
      "article_id": "abc123",
      "url": "https://x.com/i/article/abc123",
      "title": "HBM Supply Outlook",
      "author_handle": "semicapital",
      "author_name": "Semi Capital",
      "text": "HBM packaging constraints are easing slowly in 2026.",
      "captured_at": "2026-03-02T01:00:00Z"
    },
    "tweets": [],
    "captured_count": 1,
    "is_partial": false
  }'
```

### 3) Chat request

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Authorization: Bearer xic_pat_REPLACE_ME" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Bull vs bear case on HBM bottleneck from my saved items",
    "scope": "all",
    "top_k": 8
  }'
```

### 4) Configure BYOK (OpenAI) for a user

```bash
curl -X PUT http://localhost:8000/v1/model-settings \
  -H "Authorization: Bearer xic_pat_REPLACE_ME" \
  -H "Content-Type: application/json" \
  -d '{
    "inference_mode": "byok",
    "preferred_provider": "openai",
    "preferred_model": "gpt-5-mini",
    "reasoning_effort": "high",
    "byo_openai_api_key": "sk-REPLACE_ME"
  }'
```

## Extension Setup (Chrome)

1. Open `chrome://extensions`
2. Enable Developer mode
3. Click **Load unpacked**
4. Select `apps/extension`
5. Open extension options, paste PAT and API base URL (`http://localhost:8000`)
6. Save settings and use **Test Connection** to verify authentication and connectivity.
7. Visit `https://x.com/*`, use:
   - `Save Tweet`
   - `Save Thread`
   - `Save Article` (on `x.com/i/article/*` pages)
   - `Open Copilot`

Production extension configuration and exact-origin CORS setup are documented in `docs/extension-production.md`.

## Go-To-Market

The initial positioning, concierge beta process, customer acquisition cadence, monetization test, and 90-day scorecard
are documented in `docs/go-to-market-plan.md`.

Public launch configuration:

- `NEXT_PUBLIC_BETA_APPLICATION_URL` - optional POST endpoint for the private beta application form.
- `NEXT_PUBLIC_SUPPORT_EMAIL` - support and privacy contact shown on public pages.
- Review the draft privacy policy and terms with qualified counsel before public launch.

## Clerk Notes

- Web routes under `/app/*` are protected by Clerk middleware.
- Next.js route handlers forward `Authorization: Bearer <Clerk session JWT>` to FastAPI.
- If a proxied request gets `401`, the web layer refreshes the Clerk token once and retries.
- FastAPI verifies Clerk JWTs using Clerk JWKS (`CLERK_JWKS_URL`) and issuer (`CLERK_ISSUER`).
- Web users can manage model routing at `http://localhost:3000/app/settings/models`.

## Dev Notes

- DB extension init: `infra/db/init.sql` includes `CREATE EXTENSION IF NOT EXISTS vector;`
- If `EMBEDDING_MODEL`/`CHAT_MODEL` are set to `local-*`, API uses local deterministic fallback logic.
- If non-local models are configured, API calls OpenAI (`/v1/embeddings` and `/v1/chat/completions`).
- `/v1/chat` retrieves pgvector candidates, reranks them with lexical and recency signals, and asks the LLM for a natural conversational answer plus internal source-grounded claims.
- The API validates source-grounded claims against cited snippets and falls back to a conservative local response when validation fails.
- PAT handling validates token format (`xic_pat_...`) before DB lookup.
- PAT auth rejects revoked and expired tokens (`expires_at`).
- Extension PATs are stored in `chrome.storage.local`; legacy sync settings migrate automatically.
- Production API startup rejects broad extension-origin CORS regexes and accepts exact `CORS_EXTENSION_IDS`.
- `/health` now returns environment/version metadata and current `request_id`.
- Thread recaptures dedupe on root tweet identity, increment `capture_version`, and preserve immutable historical snapshots.
- `FUTURE_WORK.md` documents the planned deterministic retrieval evaluation harness.
- In-process rate limiting protects chat, ingest, and token routes. Use external/distributed rate limiting as well when running multiple API instances.
- Library dashboard filtering/search uses server query params and paged "load more" requests instead of filtering only the first client-loaded page.
