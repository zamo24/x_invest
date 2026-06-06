# X Investor Copilot Web App

Next.js App Router dashboard for the X Investor Copilot MVP.

## Responsibilities

- Protect dashboard routes under `/app/*` with Clerk middleware.
- Forward Clerk session JWTs to the FastAPI API through route handlers in `src/app/api/*`.
- Provide library, folder, chat, model settings, and API token management UI.
- Render persisted chat threads with source citations returned by the API.

## Local Development

From the repository root:

```bash
pnpm -C apps/web dev
```

The Docker compose flow is usually preferred because the web app expects the API at `API_BASE_URL`:

```bash
docker compose up --build web
```

Important environment variables:

- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`
- `CLERK_JWT_TEMPLATE` when using a custom Clerk JWT template
- `API_BASE_URL` for server-side API proxy calls
- `NEXT_PUBLIC_API_BASE_URL` for extension/onboarding copy

If Clerk keys are omitted, the app keeps a local build-friendly fallback for public pages, but authenticated dashboard workflows require Clerk.

## Validation

```bash
pnpm -C apps/web lint
pnpm -C apps/web build
pnpm -C apps/web test:e2e:list
```

Run Playwright browser tests with a web server available at `PLAYWRIGHT_BASE_URL` or `http://localhost:3000`.
