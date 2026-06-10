import { expect, test } from "@playwright/test";

test("landing page renders marketing copy", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Investor Research Copilot" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /never lose an investment thesis/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /apply for the private beta/i }).first()).toBeVisible();
});

test("public launch pages explain beta, privacy, and terms", async ({ page }) => {
  await page.goto("/beta");
  await expect(page.getByRole("heading", { name: /build a better memory/i })).toBeVisible();
  await expect(page.getByText(/applications are reviewed for fit/i)).toBeVisible();

  await page.goto("/privacy");
  await expect(page.getByRole("heading", { name: "Privacy Policy" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Chrome Limited Use disclosure/i })).toBeVisible();
  await expect(page.getByText(/historical snapshots, embeddings, and persisted chat citations/i)).toBeVisible();

  await page.goto("/terms");
  await expect(page.getByRole("heading", { name: "Terms of Service" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Not investment advice/i })).toBeVisible();
});
