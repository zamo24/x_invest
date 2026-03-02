(() => {
  const TOOLBAR_ID = "xic-toolbar-root";
  const core = globalThis.XicCaptureCore;
  let selectedFolderId = "";
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

  async function sendRuntimeMessage(type, payload) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type, payload }, resolve);
    });
  }

  function populateFolderSelect(selectEl, folders) {
    const previousSelection = selectedFolderId;
    selectEl.innerHTML = "";

    const noFolderOption = document.createElement("option");
    noFolderOption.value = "";
    noFolderOption.textContent = "No folder";
    selectEl.appendChild(noFolderOption);

    for (const folder of folders || []) {
      if (!folder?.id || !folder?.name) {
        continue;
      }
      const option = document.createElement("option");
      option.value = folder.id;
      option.textContent = folder.name;
      selectEl.appendChild(option);
    }

    const hasSelection = Array.from(selectEl.options).some((option) => option.value === previousSelection);
    selectedFolderId = hasSelection ? previousSelection : "";
    selectEl.value = selectedFolderId;
  }

  async function loadFolders(selectEl, { silent = false } = {}) {
    const response = await sendRuntimeMessage("LIST_FOLDERS");
    if (!response?.ok) {
      if (!silent) {
        showToast(response?.error || "Failed to load folders", true);
      }
      populateFolderSelect(selectEl, []);
      return;
    }

    const folders = Array.isArray(response.data) ? response.data : [];
    populateFolderSelect(selectEl, folders);
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
    return sendRuntimeMessage("INGEST_X", payload);
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
      folder_id: selectedFolderId || null,
      is_partial: false,
    };

    const response = await sendIngest(payload);
    if (!response?.ok) {
      showToast(response?.error || "Save failed", true);
      return;
    }

    showToast(selectedFolderId ? "Tweet saved to folder" : "Tweet saved");
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
      folder_id: selectedFolderId || null,
      is_partial: pendingMore,
      partial_reason: pendingMore ? "Not all replies loaded in DOM" : null,
    };

    const response = await sendIngest(payload);
    if (!response?.ok) {
      showToast(response?.error || "Thread save failed", true);
      return;
    }

    showToast(selectedFolderId ? `Thread saved to folder (${tweets.length} tweets)` : `Thread saved (${tweets.length} tweets)`);
  }

  async function saveArticle() {
    const article = core.extractArticle(document, window.location.href);
    if (!article) {
      showToast("Could not detect article content on this page", true);
      return;
    }

    const payload = {
      capture_type: "article",
      page_url: window.location.href,
      article,
      tweets: [],
      captured_count: 1,
      folder_id: selectedFolderId || null,
      is_partial: false,
    };

    const response = await sendIngest(payload);
    if (!response?.ok) {
      showToast(response?.error || "Article save failed", true);
      return;
    }

    showToast(selectedFolderId ? "Article saved to folder" : "Article saved");
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
    root.style.justifyItems = "end";
    root.style.gap = "8px";

    const btnStyle =
      "background:#0f8f75;color:#fff;border:0;border-radius:10px;padding:8px 10px;cursor:pointer;font-size:12px;box-shadow:0 6px 14px rgba(0,0,0,0.2)";
    const buttonWidth = "150px";

    const folderRow = document.createElement("div");
    folderRow.style.display = "flex";
    folderRow.style.alignItems = "center";
    folderRow.style.gap = "6px";
    folderRow.style.background = "rgba(255,255,255,0.96)";
    folderRow.style.border = "1px solid #cbd5e1";
    folderRow.style.borderRadius = "10px";
    folderRow.style.padding = "6px";
    folderRow.style.boxShadow = "0 6px 14px rgba(0,0,0,0.15)";

    const folderSelect = document.createElement("select");
    folderSelect.style.border = "1px solid #cbd5e1";
    folderSelect.style.borderRadius = "8px";
    folderSelect.style.padding = "6px 8px";
    folderSelect.style.fontSize = "12px";
    folderSelect.style.minWidth = "150px";
    folderSelect.style.background = "#fff";
    folderSelect.addEventListener("change", () => {
      selectedFolderId = folderSelect.value;
    });

    const refreshFoldersBtn = document.createElement("button");
    refreshFoldersBtn.type = "button";
    refreshFoldersBtn.textContent = "Refresh";
    refreshFoldersBtn.style.background = "#e2e8f0";
    refreshFoldersBtn.style.color = "#1e293b";
    refreshFoldersBtn.style.border = "1px solid #cbd5e1";
    refreshFoldersBtn.style.borderRadius = "8px";
    refreshFoldersBtn.style.padding = "6px 8px";
    refreshFoldersBtn.style.cursor = "pointer";
    refreshFoldersBtn.style.fontSize = "12px";
    refreshFoldersBtn.addEventListener("click", () => {
      void loadFolders(folderSelect);
    });

    folderRow.append(folderSelect, refreshFoldersBtn);

    const tweetBtn = document.createElement("button");
    tweetBtn.textContent = "Save Tweet";
    tweetBtn.setAttribute("style", btnStyle);
    tweetBtn.style.width = buttonWidth;
    tweetBtn.addEventListener("click", () => {
      void saveTweet();
    });

    const threadBtn = document.createElement("button");
    threadBtn.textContent = "Save Thread";
    threadBtn.setAttribute("style", btnStyle);
    threadBtn.style.width = buttonWidth;
    threadBtn.addEventListener("click", () => {
      void saveThread();
    });

    const articleBtn = document.createElement("button");
    articleBtn.textContent = "Save Article";
    articleBtn.setAttribute("style", btnStyle);
    articleBtn.style.width = buttonWidth;
    articleBtn.addEventListener("click", () => {
      void saveArticle();
    });

    const copilotBtn = document.createElement("button");
    copilotBtn.textContent = "Open Copilot";
    copilotBtn.setAttribute(
      "style",
      "background:#173d69;color:#fff;border:0;border-radius:10px;padding:8px 10px;cursor:pointer;font-size:12px;box-shadow:0 6px 14px rgba(0,0,0,0.2)",
    );
    copilotBtn.style.width = buttonWidth;
    copilotBtn.addEventListener("click", () => {
      void openCopilot();
    });

    root.append(folderRow, tweetBtn, threadBtn, articleBtn, copilotBtn);
    document.body.appendChild(root);

    void loadFolders(folderSelect, { silent: true });
  }

  mountToolbar();
  const observer = new MutationObserver(() => mountToolbar());
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
