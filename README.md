# X Investor Copilot (MVP)

Browser extension + web app that lets users save X (Twitter) tweets/threads and chat over a personal, source-grounded RAG library with citations to exact tweet URLs.

## Monorepo Structure

- `apps/web` - Next.js App Router dashboard + Clerk auth + token management + library/chat UI
- `apps/api` - FastAPI + SQLAlchemy + Alembic + pgvector ingest/retrieval/chat APIs
- `apps/extension` - Manifest V3 extension (options PAT, content script save actions, side panel chat)
- `infra/docker-compose.yml` - Local dev compose stack

## Prerequisites

- Docker + Docker Compose
- Node 20+
- pnpm 10+
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

3. Set `TOKEN_PEPPER` to a long random string.

4. For OpenAI-backed embeddings + chat (step 2), set:

- `OPENAI_API_KEY` (or `LLM_API_KEY`)
- `EMBEDDING_MODEL=text-embedding-3-small`
- `CHAT_MODEL=gpt-4o-mini`
- `EMBEDDING_DIM=256` (keeps compatibility with current pgvector schema)
- Optional: `OPENAI_BASE_URL`, `OPENAI_TIMEOUT_SECONDS`

## Run Locally (Docker)

From repo root:

```bash
docker compose up --build
```

Services:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Postgres: `localhost:55432`

`api` container runs migrations at startup:

```bash
alembic upgrade head
```

## Run With Infra Compose File

```bash
docker compose -f infra/docker-compose.yml up --build
```

## API Endpoints (MVP)

- `POST /v1/tokens` (Bearer Clerk JWT) create PAT
- `GET /v1/tokens` list PATs
- `DELETE /v1/tokens/{id}` revoke PAT
- `POST /v1/ingest/x` (Bearer PAT) ingest tweet/thread capture
- `POST /v1/chat` (Bearer PAT or Bearer Clerk JWT) source-grounded chat
- `GET /v1/library/items` (Bearer PAT or Bearer Clerk JWT)
- `GET /v1/library/threads` (Bearer PAT or Bearer Clerk JWT)
- `GET /v1/library/threads/{id}` (Bearer PAT or Bearer Clerk JWT)

## Curl Examples

### 1) Create token (web/Clerk context)

Best path: create/revoke tokens in the dashboard at `http://localhost:3000/app/settings/tokens`.

Direct API example (requires a valid Clerk session JWT):

```bash
curl -X POST http://localhost:8000/v1/tokens \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer CLERK_SESSION_JWT" \
  -d '{"name":"Extension PAT"}'
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

## Extension Setup (Chrome)

1. Open `chrome://extensions`
2. Enable Developer mode
3. Click **Load unpacked**
4. Select `apps/extension`
5. Open extension options, paste PAT and API base URL (`http://localhost:8000`)
6. Visit `https://x.com/*`, use:
   - `Save Tweet`
   - `Save Thread`
   - `Open Copilot`

## Clerk Notes

- Web routes under `/app/*` are protected by Clerk middleware.
- Next.js route handlers forward `Authorization: Bearer <Clerk session JWT>` to FastAPI.
- FastAPI verifies Clerk JWTs using Clerk JWKS (`CLERK_JWKS_URL`) and issuer (`CLERK_ISSUER`).

## Dev Notes

- DB extension init: `infra/db/init.sql` includes `CREATE EXTENSION IF NOT EXISTS vector;`
- If `EMBEDDING_MODEL`/`CHAT_MODEL` are set to `local-*`, API uses local deterministic fallback logic.
- If non-local models are configured, API calls OpenAI (`/v1/embeddings` and `/v1/chat/completions`).
- `/v1/chat` enforces source-grounded output with citations and marks unsupported claims as `Unknown / Speculation`.
