import { expect, test, type Page } from "@playwright/test";

const now = "2026-03-02T16:00:00.000Z";

async function mockDashboardApi(page: Page) {
  let chatThreads: unknown[] = [];
  let chatMessages: unknown[] = [];

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/api/library/folders") {
      await route.fulfill({
        json: [
          {
            id: "folder-hbm",
            name: "HBM",
            created_at: now,
            item_count: 1,
            thread_count: 1,
          },
        ],
      });
      return;
    }

    if (path === "/api/library/threads") {
      await route.fulfill({
        json: [
          {
            id: "thread-hbm",
            root_tweet_id: "100",
            root_url: "https://x.com/semicapital/status/100",
            title: "HBM thesis update",
            captured_at: now,
            capture_version: 2,
            is_partial: false,
            item_count: 3,
            author_handles: ["semicapital"],
            folder_id: "folder-hbm",
            folder_name: "HBM",
          },
        ],
      });
      return;
    }

    if (path === "/api/library/items") {
      await route.fulfill({
        json: [
          {
            id: "item-article",
            tweet_id: "article-1",
            url: "https://x.com/i/article/article-1",
            author_handle: "semicapital",
            author_name: "Semi Capital",
            created_at: now,
            captured_at: now,
            text: "HBM packaging capacity is improving but demand still exceeds supply.",
            source_kind: "article",
            title: "HBM Supply Outlook",
            folder_id: "folder-hbm",
            folder_name: "HBM",
          },
        ],
      });
      return;
    }

    if (path === "/api/chat/threads" && request.method() === "GET") {
      await route.fulfill({ json: chatThreads });
      return;
    }

    if (path === "/api/chat" && request.method() === "POST") {
      chatThreads = [
        {
          id: "chat-hbm",
          title: "Summarize the HBM supply view",
          created_at: now,
          updated_at: now,
          last_message_at: now,
          message_count: 2,
        },
      ];
      chatMessages = [
        {
          id: "msg-user",
          role: "user",
          message_text: "Summarize the HBM supply view",
          cited_sources: [],
          provider_used: null,
          model_used: null,
          inference_mode_used: null,
          reasoning_effort_used: null,
          created_at: now,
        },
        {
          id: "msg-assistant",
          role: "assistant",
          message_text:
            "Your saved source suggests HBM supply remains tight, although packaging capacity is improving.",
          cited_sources: [
            {
              tweet_url: "https://x.com/semicapital/status/100",
              tweet_id: "100",
              author_handle: "semicapital",
              created_at: now,
              snippet: "HBM packaging capacity is improving but demand still exceeds supply.",
            },
          ],
          provider_used: "openai",
          model_used: "gpt-4o-mini",
          inference_mode_used: "hosted",
          reasoning_effort_used: "none",
          created_at: now,
        },
      ];
      await route.fulfill({
        json: {
          chat_thread_id: "chat-hbm",
          answer_text: "Your saved source suggests HBM supply remains tight.",
          cited_sources: [
            {
              tweet_url: "https://x.com/semicapital/status/100",
              tweet_id: "100",
              author_handle: "semicapital",
              created_at: now,
              snippet: "HBM packaging capacity is improving but demand still exceeds supply.",
            },
          ],
        },
      });
      return;
    }

    if (path === "/api/chat/threads/chat-hbm") {
      await route.fulfill({
        json: {
          thread: {
            id: "chat-hbm",
            title: "Summarize the HBM supply view",
            created_at: now,
            updated_at: now,
            last_message_at: now,
            message_count: 2,
          },
          messages: chatMessages,
        },
      });
      return;
    }

    await route.fulfill({ status: 404, json: { detail: `Unhandled test route: ${path}` } });
  });
}

test("library dashboard renders saved threads, items, and filters", async ({ page }) => {
  await mockDashboardApi(page);

  await page.goto("/app/library");

  await expect(page.getByRole("heading", { name: "Library" })).toBeVisible();
  await expect(page.getByText("HBM thesis update")).toBeVisible();
  await expect(page.getByText("HBM Supply Outlook")).toBeVisible();
  await expect(page.getByText("v2")).toBeVisible();

  await page.getByPlaceholder("Search text, title, URL, author, tweet ID...").fill("supply");
  await expect(page.getByText("HBM Supply Outlook")).toBeVisible();
});

test("chat dashboard sends a question and renders persisted cited response", async ({ page }) => {
  await mockDashboardApi(page);

  await page.goto("/app/chat");

  await page.getByPlaceholder("Message Investor Copilot...").fill("Summarize the HBM supply view");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Summarize the HBM supply view").first()).toBeVisible();
  await expect(
    page.getByText("Your saved source suggests HBM supply remains tight, although packaging capacity is improving."),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "https://x.com/semicapital/status/100" }).first()).toBeVisible();
});
