(function registerXUrlCore(globalObject) {
  const POST_RE = /^https:\/\/(?:www\.)?x\.com\/[A-Za-z0-9_]{1,15}\/status\/\d+(?:[/?#].*)?$/i;

  function validatePostUrl(value) {
    const url = String(value || "").trim();
    if (!POST_RE.test(url)) {
      throw new Error("Open a canonical x.com post URL before saving.");
    }
    return url;
  }

  function buildSavePayload(url, folderId, mode) {
    if (!["post", "author_thread"].includes(mode)) {
      throw new Error("Unsupported save mode.");
    }
    return {
      url: validatePostUrl(url),
      folder_id: folderId || null,
      mode,
    };
  }

  globalObject.XicXUrlCore = { buildSavePayload, validatePostUrl };
})(typeof globalThis !== "undefined" ? globalThis : window);
