(() => {
  const TOOLBAR_ID = "xic-toolbar-root";
  const core = globalThis.XicCaptureCore;
  if (!core) {
    console.error("XicCaptureCore is missing. Did capture-core.js load?");
    return;
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function showToast(message, isError = false) {
    const toast = document.createElement("div");
    toast.textContent = message;
    toast.style.position = "fixed";
    toast.style.right = "16px";
    toast.style.bottom = "16px";
    toast.style.zIndex = "999999";
    toast.style.padding = "10px 12px";
    toast.style.borderRadius = "10px";
    toast.style.background = isError ? "#a32727" : "#176d5f";
    toast.style.color = "#fff";
    toast.style.fontSize = "13px";
    toast.style.boxShadow = "0 10px 20px rgba(0,0,0,0.25)";
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2400);
  }

  async function expandLoadedThread(maxPasses = 8) {
    const triggerTexts = ["Show more", "Read more", "Show replies", "Show more replies"];

    for (let i = 0; i < maxPasses; i += 1) {
      const buttons = Array.from(document.querySelectorAll("div[role='button']"));
      const target = buttons.find((button) => {
        const text = button.textContent || "";
        return triggerTexts.some((needle) => text.includes(needle));
      });

      if (!target) {
        return;
      }

      target.click();
      await sleep(350);
    }
  }

  function findCurrentTweetArticle() {
    const currentPath = window.location.pathname;
    const all = Array.from(document.querySelectorAll("article[data-testid='tweet']"));
    const exact = all.find((article) => {
      const statusAnchor = article.querySelector("a[href*='/status/']");
      const href = statusAnchor?.getAttribute("href") || "";
      return href && currentPath.includes(href);
    });
    return exact || all[0] || null;
  }

  async function sendIngest(payload) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: "INGEST_X", payload }, resolve);
    });
  }

  async function saveTweet() {
    const article = findCurrentTweetArticle();
    if (!article) {
      showToast("Could not find tweet on page", true);
      return;
    }

    const tweet = core.extractTweet(article);
    if (!tweet) {
      showToast("Could not parse tweet text", true);
      return;
    }

    const payload = {
      capture_type: "tweet",
      page_url: window.location.href,
      root_tweet_id: tweet.tweet_id,
      root_tweet_url: tweet.url,
      tweets: [tweet],
      captured_count: 1,
      is_partial: false,
    };

    const response = await sendIngest(payload);
    if (!response?.ok) {
      showToast(response?.error || "Save failed", true);
      return;
    }

    showToast("Tweet saved");
  }

  async function saveThread() {
    await expandLoadedThread();
    const tweets = core.collectVisibleTweets(document);
    if (!tweets.length) {
      showToast("No tweets found in current thread view", true);
      return;
    }

    const rootUrl = window.location.href;
    const rootTweetId = core.parseTweetIdFromUrl(rootUrl) || tweets[0]?.tweet_id || null;

    const pendingMore = Array.from(document.querySelectorAll("div[role='button']")).some((button) => {
      const text = button.textContent || "";
      return text.includes("Show more replies") || text.includes("Show replies");
    });

    const payload = {
      capture_type: "thread",
      page_url: window.location.href,
      root_tweet_id: rootTweetId,
      root_tweet_url: rootUrl,
      tweets,
      captured_count: tweets.length,
      is_partial: pendingMore,
      partial_reason: pendingMore ? "Not all replies loaded in DOM" : null,
    };

    const response = await sendIngest(payload);
    if (!response?.ok) {
      showToast(response?.error || "Thread save failed", true);
      return;
    }

    showToast(`Thread saved (${tweets.length} tweets)`);
  }

  async function openCopilot() {
    chrome.runtime.sendMessage({ type: "OPEN_SIDE_PANEL" }, () => {
      showToast("Copilot opened");
    });
  }

  function mountToolbar() {
    if (document.getElementById(TOOLBAR_ID)) {
      return;
    }

    const root = document.createElement("div");
    root.id = TOOLBAR_ID;
    root.style.position = "fixed";
    root.style.right = "16px";
    root.style.top = "72px";
    root.style.zIndex = "999999";
    root.style.display = "grid";
    root.style.gap = "8px";

    const btnStyle =
      "background:#0f8f75;color:#fff;border:0;border-radius:10px;padding:8px 10px;cursor:pointer;font-size:12px;box-shadow:0 6px 14px rgba(0,0,0,0.2)";

    const tweetBtn = document.createElement("button");
    tweetBtn.textContent = "Save Tweet";
    tweetBtn.setAttribute("style", btnStyle);
    tweetBtn.addEventListener("click", () => {
      void saveTweet();
    });

    const threadBtn = document.createElement("button");
    threadBtn.textContent = "Save Thread";
    threadBtn.setAttribute("style", btnStyle);
    threadBtn.addEventListener("click", () => {
      void saveThread();
    });

    const copilotBtn = document.createElement("button");
    copilotBtn.textContent = "Open Copilot";
    copilotBtn.setAttribute(
      "style",
      "background:#173d69;color:#fff;border:0;border-radius:10px;padding:8px 10px;cursor:pointer;font-size:12px;box-shadow:0 6px 14px rgba(0,0,0,0.2)",
    );
    copilotBtn.addEventListener("click", () => {
      void openCopilot();
    });

    root.append(tweetBtn, threadBtn, copilotBtn);
    document.body.appendChild(root);
  }

  mountToolbar();
  const observer = new MutationObserver(() => mountToolbar());
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
