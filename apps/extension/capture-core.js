(function registerCaptureCore(globalObject) {
  const TOKEN_RE = /^\/[A-Za-z0-9_]{1,15}$/;

  function parseTweetIdFromUrl(url) {
    const match = (url || "").match(/\/status\/(\d+)/);
    return match ? match[1] : null;
  }

  function detectHandle(article) {
    const anchors = Array.from(article.querySelectorAll("a[href^='/'], a[href*='x.com/']"));
    for (const anchor of anchors) {
      const href = anchor.getAttribute("href") || "";
      if (TOKEN_RE.test(href)) {
        return href.slice(1);
      }

      try {
        const pathname = new URL(anchor.href).pathname;
        if (TOKEN_RE.test(pathname)) {
          return pathname.slice(1);
        }
      } catch {
        // ignore malformed URL
      }
    }
    return "unknown";
  }

  function extractTweet(article) {
    const statusAnchors = Array.from(article.querySelectorAll("a[href*='/status/']"));
    const statusAnchor = statusAnchors[0];
    if (!statusAnchor) {
      return null;
    }

    const href = statusAnchor.getAttribute("href") || statusAnchor.href || "";
    const url = href.startsWith("http") ? href : `https://x.com${href}`;
    const tweetId = parseTweetIdFromUrl(url);
    const textNodes = Array.from(article.querySelectorAll("div[data-testid='tweetText']"));
    const text = textNodes
      .map((el) => el.textContent?.trim() || "")
      .filter(Boolean)
      .join("\n")
      .trim();

    if (!text) {
      return null;
    }

    const authorName =
      article.querySelector("div[data-testid='User-Name'] span")?.textContent?.trim() || detectHandle(article);

    let quoted = null;
    if (statusAnchors.length > 1 || textNodes.length > 1) {
      const quotedAnchor = statusAnchors.find((anchor) => {
        const qHref = anchor.getAttribute("href") || anchor.href || "";
        return qHref && qHref !== href;
      });

      const quotedUrl = quotedAnchor ? (quotedAnchor.getAttribute("href") || quotedAnchor.href || "") : "";
      const normalizedQuotedUrl = quotedUrl ? (quotedUrl.startsWith("http") ? quotedUrl : `https://x.com${quotedUrl}`) : null;
      const quotedText = (textNodes[1]?.textContent || "").trim() || null;

      if (normalizedQuotedUrl || quotedText) {
        quoted = {
          tweet_id: normalizedQuotedUrl ? parseTweetIdFromUrl(normalizedQuotedUrl) : null,
          url: normalizedQuotedUrl,
          text: quotedText || "",
          author_handle: quotedAnchor ? detectHandle(quotedAnchor.closest("article") || article) : null,
          author_name: null,
          created_at: null,
        };
      }
    }

    return {
      tweet_id: tweetId,
      url,
      author_handle: detectHandle(article),
      author_name: authorName,
      text,
      quoted,
      captured_at: new Date().toISOString(),
    };
  }

  function collectVisibleTweets(doc) {
    return Array.from(doc.querySelectorAll("article[data-testid='tweet']"))
      .map((article) => extractTweet(article))
      .filter(Boolean);
  }

  globalObject.XicCaptureCore = {
    collectVisibleTweets,
    detectHandle,
    extractTweet,
    parseTweetIdFromUrl,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);
