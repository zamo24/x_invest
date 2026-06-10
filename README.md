# Investor Research Copilot

Connect your X account and turn bookmarks and saved posts into a searchable, source-cited research
library. The product name is configurable with `NEXT_PUBLIC_PRODUCT_NAME` and defaults to Investor
Research Copilot. X is an integration; the product is not affiliated with X.

## Architecture

- `apps/api`: FastAPI, PostgreSQL, SQLAlchemy, Alembic, pgvector, official X API integration.
- `apps/web`: Next.js dashboard with Clerk authentication.
- `apps/extension`: Chrome Manifest V3 URL-only save actions, PAT authentication, folders, and chat.
- `docs/x-api-architecture.md`: data flow and storage boundaries.
- `docs/x-api-operations.md`: developer-console setup and operations.
- `docs/x-api-compliance.md`: implemented controls, approval gates, and deferred compliance work.

The extension does not read X page DOM, inject scripts, expand replies, or extract X Article bodies.
After an explicit action it sends only the active X post URL, optional folder ID, and save mode to the
application API. The API retrieves content server-side through official X API endpoints.

## Local Setup

Requirements: Docker, Docker Compose, Node 20+, pnpm 9+, and optionally Python 3.11+.

```bash
cp .env.example .env
docker compose up --build
```

The deterministic local development path does not require model or X credentials:

```text
EMBEDDING_MODEL=local-hash-v1
CHAT_MODEL=local-grounded-v1
```

Live X connection requires a confidential Web App configured for OAuth 2.0 Authorization Code Flow
with PKCE and an exact callback matching `X_REDIRECT_URI`.

Required scopes:

- `tweet.read`
- `users.read`
- `bookmark.read`
- `offline.access`

Do not request bookmark-write or post-write permissions.

Required production variables:

```text
X_CLIENT_ID
X_CLIENT_SECRET
X_REDIRECT_URI
X_TOKEN_ENCRYPTION_KEY
```

See `.env.example` for usage budgets, revalidation cadence, Clerk, CORS, and model configuration.

## Primary Workflows

- Connect or disconnect X at `/app/settings/x`.
- Sync bookmarks as the primary ingestion workflow.
- Save an X post URL through the dashboard or extension.
- Save an author thread on a best-effort basis.
- Search the library and ask source-cited questions.
- Inspect immutable historical thread captures.

Full-body X Article capture is unsupported. Conversation reconstruction is always best effort because
search access, age, pagination, deleted content, and permissions can prevent guaranteed completeness.

## API

Official X integration endpoints:

- `GET /v1/integrations/x/status`
- `POST /v1/integrations/x/authorize`
- `GET /v1/integrations/x/callback`
- `DELETE /v1/integrations/x`
- `POST /v1/integrations/x/bookmarks/sync`
- `POST /v1/sources/x`

Example save request:

```bash
curl -X POST http://localhost:8000/v1/sources/x \
  -H "Authorization: Bearer xic_pat_REPLACE_ME" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://x.com/user/status/123","folder_id":null,"mode":"post"}'
```

Existing library, folders, chat, model settings, and PAT endpoints remain available. Extension PATs
are HMAC-hashed; X access tokens, refresh tokens, and PKCE verifiers are encrypted at rest.

## Revalidation

```bash
cd apps/api
python -m app.cli.revalidate_x
```

Revalidation batches current X post IDs, updates changed current content and embeddings, and marks
unavailable current sources. It is safe to retry.

## Validation

```bash
docker compose run --rm --build -e EMBEDDING_MODEL=local-hash-v1 -e CHAT_MODEL=local-grounded-v1 api python -m pytest -q
pnpm -C apps/extension test
pnpm -C apps/web lint
pnpm -C apps/web build
pnpm -C apps/web test:e2e:list
git diff --check
```

Automated tests mock external X API calls and do not require live X credentials.

## Compliance Status

This is a compliance-oriented technical redesign, not a guarantee of legal or X policy compliance.
Production launch requires legal review, X developer access and endpoint approval, and written X
confirmation of the retention model.

This phase intentionally preserves immutable historical X content and does not propagate X content
deletion or modification events through historical snapshots, historical embeddings, or persisted
chat citations. Do not describe the system as fully compliant with X policies until legal review and
written X approval confirm this model. See `docs/x-api-compliance.md`.
