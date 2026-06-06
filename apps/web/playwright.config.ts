import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3100";
const shouldStartWebServer = !process.env.PLAYWRIGHT_BASE_URL && process.env.PLAYWRIGHT_SKIP_WEB_SERVER !== "1";
const reuseExistingServer = process.env.PLAYWRIGHT_REUSE_SERVER === "1";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  webServer: shouldStartWebServer
    ? {
        command: "pnpm dev --hostname 127.0.0.1 --port 3100",
        url: baseURL,
        reuseExistingServer,
        timeout: 120_000,
        env: {
          E2E_BYPASS_CLERK_AUTH: "true",
        },
      }
    : undefined,
});
