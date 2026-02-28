# apps/web/Dockerfile
FROM node:20-alpine AS base
WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@9.0.0 --activate

# ---- deps ----
FROM base AS deps
# Copy workspace manifests
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
# Copy only the web package manifest first (better cache)
COPY apps/web/package.json apps/web/package.json

# Install deps needed for web (and its workspace graph if any)
RUN pnpm install --frozen-lockfile --filter web...

# ---- builder ----
FROM base AS builder
# Copy the full web app
COPY apps/web ./apps/web
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/web/node_modules ./apps/web/node_modules
COPY --from=deps /repo/pnpm-lock.yaml ./pnpm-lock.yaml
COPY --from=deps /repo/package.json ./package.json
COPY --from=deps /repo/pnpm-workspace.yaml ./pnpm-workspace.yaml

# Build web
RUN pnpm --filter web build

# ---- runner ----
FROM node:20-alpine AS runner
WORKDIR /repo/apps/web
ENV NODE_ENV=production
RUN corepack enable && corepack prepare pnpm@9.0.0 --activate

# Copy only what's needed to run
COPY --from=builder /repo/apps/web/.next ./.next
COPY --from=builder /repo/apps/web/public ./public
COPY --from=builder /repo/apps/web/package.json ./package.json
COPY --from=builder /repo/node_modules /repo/node_modules
COPY --from=builder /repo/apps/web/node_modules ./node_modules
COPY --from=builder /repo/pnpm-lock.yaml /repo/pnpm-lock.yaml

EXPOSE 3000
CMD ["pnpm", "start", "-p", "3000"]
