importScripts("settings-core.js", "x-url-core.js");

const settingsCore = globalThis.XicSettingsCore;

async function apiRequest(path, options = {}) {
  const { method = "POST", payload = null, settings = null } = options;
  const resolvedSettings = settings || (await settingsCore.readSettings());
  const pat = settingsCore.validatePat(resolvedSettings.pat);
  const apiBase = settingsCore.normalizeApiBase(resolvedSettings.apiBase);

  const hasPermission = await chrome.permissions.contains({
    origins: [settingsCore.permissionOrigin(apiBase)],
  });
  if (!hasPermission) {
    throw new Error("The extension does not have permission for this API origin. Open extension options and save settings.");
  }

  const headers = {
    Authorization: `Bearer ${pat}`,
  };

  if (payload !== null) {
    headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(`${apiBase}${path}`, {
      method,
      headers,
      body: payload !== null ? JSON.stringify(payload) : undefined,
    });
  } catch (error) {
    throw new Error(`Could not reach the configured API. Verify the URL, network, and API CORS settings. (${error})`);
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(settingsCore.apiErrorMessage(response.status, data));
  }

  return data;
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    if (message?.type === "SAVE_CURRENT_X") {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const payload = globalThis.XicXUrlCore.buildSavePayload(
        tab?.url,
        message?.payload?.folder_id,
        message?.payload?.mode,
      );
      const data = await apiRequest("/v1/sources/x", { method: "POST", payload });
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

    if (message?.type === "TEST_CONNECTION") {
      const pat = settingsCore.validatePat(message?.payload?.pat);
      const apiBase = settingsCore.normalizeApiBase(message?.payload?.api_base);
      const data = await apiRequest("/v1/me", {
        method: "GET",
        settings: { pat, apiBase },
      });
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
