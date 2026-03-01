import { expect, test } from "@playwright/test";

test("landing page renders marketing copy", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("X Investor Copilot")).toBeVisible();
  await expect(page.getByRole("heading", { name: /personal rag copilot/i })).toBeVisible();
});
