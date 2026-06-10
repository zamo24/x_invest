import { expect, test, type Page } from "@playwright/test";

const now = "2026-03-02T16:00:00.000Z";

async function mockDashboardApi(page: Page) {
  let chatThreads: unknown[] = [];
  let chatMessages: unknown[] = [];
  let xConnected = false;

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/api/integrations/x/status") {
      await route.fulfill({
        json: {
          connected: xConnected,
          status: xConnected ? "connected" : "disconnected",
          x_user_id: xConnected ? "x-user" : null,
          x_username: xConnected ? "researcher" : null,
          granted_scopes: xConnected ? ["tweet.read", "users.read", "bookmark.read", "offline.access"] : [],
          connected_at: xConnected ? now : null,
          last_bookmark_sync_at: null,
          last_bookmark_sync_result: null,
          monthly_post_reads: 12,
          monthly_post_read_budget: 1000,
        },
      });
      return;
    }

    if (path === "/api/integrations/x/authorize") {
      await route.fulfill({ json: { authorization_url: "/app/settings/x?connected=1", expires_at: now } });
      return;
    }

    if (path === "/api/integrations/x" && request.method() === "DELETE") {
      xConnected = false;
      await route.fulfill({ json: { status: "disconnected" } });
      return;
    }

    if (path === "/api/integrations/x/bookmarks/sync") {
      await route.fulfill({ json: { fetched: 4, created: 2, updated: 1, unavailable: 0, failed: 0, folders_mapped: 1, partial: false } });
      return;
    }

    if (path === "/api/sources/x") {
      await route.fulfill({ json: { item_ids: ["saved"], created: 1, updated: 0, is_partial: false } });
      return;
    }

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

    if (path === "/api/library/threads/thread-hbm") {
      const requestedVersion = url.searchParams.get("version") || "2";
      const isLatest = requestedVersion === "2";
      await route.fulfill({
        json: {
          thread: {
            id: "thread-hbm",
            root_tweet_id: "100",
            root_url: "https://x.com/semicapital/status/100",
            title: "HBM thesis update",
            captured_at: now,
            capture_version: 2,
            is_partial: false,
            item_count: 1,
            author_handles: ["semicapital"],
            folder_id: "folder-hbm",
            folder_name: "HBM",
          },
          selected_capture: {
            id: isLatest ? "capture-2" : "capture-1",
            capture_version: isLatest ? 2 : 1,
            captured_at: now,
            is_partial: !isLatest,
            partial_reason: isLatest ? null : "Replies still loading",
            item_count: 1,
          },
          captures: [
            {
              id: "capture-2",
              capture_version: 2,
              captured_at: now,
              is_partial: false,
              partial_reason: null,
              item_count: 1,
            },
            {
              id: "capture-1",
              capture_version: 1,
              captured_at: now,
              is_partial: true,
              partial_reason: "Replies still loading",
              item_count: 1,
            },
          ],
          items: [
            {
              id: "item-thread",
              item_order: 0,
              tweet_id: "100",
              url: "https://x.com/semicapital/status/100",
              author_handle: "semicapital",
              author_name: "Semi Capital",
              created_at: now,
              captured_at: now,
              text: isLatest ? "Latest HBM thesis snapshot." : "Original HBM thesis snapshot.",
            },
          ],
        },
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

  await page.getByPlaceholder("Search text, title, URL, author, post ID...").fill("supply");
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

test("thread detail switches between immutable capture versions", async ({ page }) => {
  await mockDashboardApi(page);

  await page.goto("/app/threads/thread-hbm");
  await expect(page.getByText("Latest HBM thesis snapshot.")).toBeVisible();

  await page.locator("select").selectOption("1");
  await expect(page.getByText("Original HBM thesis snapshot.")).toBeVisible();
  await expect(page.getByText(/Replies still loading/)).toBeVisible();
});

test("X integration settings supports bookmark sync, save-by-URL, and disconnect", async ({ page }) => {
  await mockDashboardApi(page);
  await page.goto("/app/settings/x");
  await expect(page.getByRole("heading", { name: "X Integration" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Connect X" })).toBeVisible();

  // Re-register with connected state by intercepting status directly for the operational controls.
  await page.route("**/api/integrations/x/status", (route) =>
    route.fulfill({
      json: {
        connected: true,
        status: "connected",
        x_username: "researcher",
        granted_scopes: ["tweet.read", "users.read", "bookmark.read", "offline.access"],
        monthly_post_reads: 12,
        monthly_post_read_budget: 1000,
      },
    }),
  );
  await page.reload();
  await expect(page.getByRole("button", { name: "Sync bookmarks" })).toBeVisible();
  await page.getByPlaceholder("https://x.com/user/status/123").fill("https://x.com/researcher/status/123");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Post saved through the official X API.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Disconnect X" })).toBeVisible();
});
