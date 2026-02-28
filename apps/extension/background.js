const DEFAULT_API_BASE = "http://localhost:8000";

async function readSettings() {
  const { xic_pat, xic_api_base } = await chrome.storage.sync.get(["xic_pat", "xic_api_base"]);
  return {
    pat: xic_pat || "",
    apiBase: xic_api_base || DEFAULT_API_BASE,
  };
}

async function apiRequest(path, payload) {
  const { pat, apiBase } = await readSettings();

  if (!pat) {
    throw new Error("No PAT configured. Open extension options and add your token.");
  }

  const response = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${pat}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
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
      const data = await apiRequest("/v1/ingest/x", message.payload);
      sendResponse({ ok: true, data });
      return;
    }

    if (message?.type === "CHAT") {
      const data = await apiRequest("/v1/chat", message.payload);
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
