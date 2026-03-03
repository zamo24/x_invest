const DEFAULT_API_BASE = "http://localhost:8000";

async function readSettings() {
  const { xic_pat, xic_api_base } = await chrome.storage.sync.get(["xic_pat", "xic_api_base"]);
  return {
    pat: xic_pat || "",
    apiBase: xic_api_base || DEFAULT_API_BASE,
  };
}

async function apiRequest(path, options = {}) {
  const { method = "POST", payload = null } = options;
  const { pat, apiBase } = await readSettings();

  if (!pat) {
    throw new Error("No PAT configured. Open extension options and add your token.");
  }

  const headers = {
    Authorization: `Bearer ${pat}`,
  };

  if (payload !== null) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${apiBase}${path}`, {
    method,
    headers,
    body: payload !== null ? JSON.stringify(payload) : undefined,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.detail || "API request failed");
  }

  return data;
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    if (message?.type === "INGEST_X") {
      const data = await apiRequest("/v1/ingest/x", { method: "POST", payload: message.payload });
      sendResponse({ ok: true, data });
      return;
    }

    if (message?.type === "CHAT") {
      const data = await apiRequest("/v1/chat", { method: "POST", payload: message.payload });
      sendResponse({ ok: true, data });
      return;
    }

    if (message?.type === "CHAT_THREADS") {
      const data = await apiRequest("/v1/chat/threads", { method: "GET" });
      sendResponse({ ok: true, data });
      return;
    }

    if (message?.type === "CHAT_THREAD_DETAIL") {
      const threadId = message?.payload?.thread_id;
      if (!threadId) {
        sendResponse({ ok: false, error: "thread_id is required" });
        return;
      }
      const data = await apiRequest(`/v1/chat/threads/${threadId}`, { method: "GET" });
      sendResponse({ ok: true, data });
      return;
    }

    if (message?.type === "LIST_FOLDERS") {
      const data = await apiRequest("/v1/library/folders", { method: "GET" });
      sendResponse({ ok: true, data });
      return;
    }

    if (message?.type === "OPEN_SIDE_PANEL") {
      if (sender.tab?.id) {
        await chrome.sidePanel.open({ tabId: sender.tab.id });
      }
      sendResponse({ ok: true });
      return;
    }

    sendResponse({ ok: false, error: "Unsupported message" });
  })().catch((error) => {
    sendResponse({ ok: false, error: error instanceof Error ? error.message : String(error) });
  });

  return true;
});
