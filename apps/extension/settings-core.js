(function registerSettingsCore(globalObject) {
  const DEFAULT_API_BASE = "http://localhost:8000";
  const PAT_RE = /^xic_pat_[A-Za-z0-9_-]{20,}$/;
  const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);

  function validatePat(value) {
    const pat = (value || "").trim();
    if (!PAT_RE.test(pat)) {
      throw new Error("Enter a valid PAT beginning with xic_pat_.");
    }
    return pat;
  }

  function normalizeApiBase(value) {
    const raw = (value || DEFAULT_API_BASE).trim();
    let parsed;
    try {
      parsed = new URL(raw);
    } catch {
      throw new Error("Enter a valid API base URL.");
    }

    const isLocalHttp = parsed.protocol === "http:" && LOCAL_HOSTS.has(parsed.hostname);
    if (parsed.protocol !== "https:" && !isLocalHttp) {
      throw new Error("Production API URLs must use HTTPS. HTTP is allowed only for local development.");
    }
    if (parsed.username || parsed.password || parsed.search || parsed.hash) {
      throw new Error("API base URL cannot include credentials, query parameters, or fragments.");
    }

    parsed.pathname = parsed.pathname.replace(/\/+$/, "");
    return parsed.toString().replace(/\/$/, "");
  }

  function permissionOrigin(apiBase) {
    const parsed = new URL(normalizeApiBase(apiBase));
    return `${parsed.origin}/*`;
  }

  function apiErrorMessage(status, payload) {
    const detail = typeof payload?.detail === "string" ? payload.detail : "";
    if (status === 401) {
      return "Authentication failed. Create a new extension PAT in the dashboard and update these settings.";
    }
    if (status === 403) {
      return "The API denied this extension request. Verify the production extension ID is allowed by API CORS.";
    }
    if (status === 429) {
      return "The API rate limit was reached. Wait briefly and try again.";
    }
    return detail || `API request failed with status ${status}.`;
  }

  async function readSettings(chromeApi = chrome) {
    const local = await chromeApi.storage.local.get(["xic_pat", "xic_api_base"]);
    if (local.xic_pat || local.xic_api_base) {
      return {
        pat: local.xic_pat || "",
        apiBase: local.xic_api_base || DEFAULT_API_BASE,
      };
    }

    const synced = await chromeApi.storage.sync.get(["xic_pat", "xic_api_base"]);
    if (synced.xic_pat || synced.xic_api_base) {
      const migrated = {
        xic_pat: synced.xic_pat || "",
        xic_api_base: synced.xic_api_base || DEFAULT_API_BASE,
      };
      await chromeApi.storage.local.set(migrated);
      await chromeApi.storage.sync.remove(["xic_pat", "xic_api_base"]);
      return {
        pat: migrated.xic_pat,
        apiBase: migrated.xic_api_base,
      };
    }

    return { pat: "", apiBase: DEFAULT_API_BASE };
  }

  async function saveSettings({ pat, apiBase }, chromeApi = chrome) {
    const normalized = {
      xic_pat: validatePat(pat),
      xic_api_base: normalizeApiBase(apiBase),
    };
    await chromeApi.storage.local.set(normalized);
    await chromeApi.storage.sync.remove(["xic_pat", "xic_api_base"]);
    return {
      pat: normalized.xic_pat,
      apiBase: normalized.xic_api_base,
    };
  }

  globalObject.XicSettingsCore = {
    DEFAULT_API_BASE,
    apiErrorMessage,
    normalizeApiBase,
    permissionOrigin,
    readSettings,
    saveSettings,
    validatePat,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);
