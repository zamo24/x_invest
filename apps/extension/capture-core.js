(function registerCaptureCore(globalObject) {
  const TOKEN_RE = /^\/[A-Za-z0-9_]{1,15}$/;

  function parseTweetIdFromUrl(url) {
    const match = (url || "").match(/\/status\/(\d+)/);
    return match ? match[1] : null;
  }

  function parseArticleIdFromUrl(url) {
    const match = (url || "").match(/\/i\/articles?\/([A-Za-z0-9:_-]+)/i);
    return match ? match[1] : null;
  }

  function normalizeUrl(candidate, fallbackUrl) {
    if (!candidate) {
      return null;
    }
    try {
      return new URL(candidate, fallbackUrl || window.location.href).toString();
    } catch {
      return null;
    }
  }

  function detectArticleUrl(doc, fallbackUrl) {
    const candidates = [
      doc.querySelector("link[rel='canonical']")?.getAttribute("href") || "",
      doc.querySelector("meta[property='og:url']")?.getAttribute("content") || "",
      doc.querySelector("meta[name='twitter:url']")?.getAttribute("content") || "",
    ];

    const directAnchor = doc.querySelector("a[href*='/i/article/'], a[href*='/i/articles/']");
    if (directAnchor) {
      candidates.push(directAnchor.getAttribute("href") || "");
    }

    candidates.push(fallbackUrl || "");

    for (const candidate of candidates) {
      const normalized = normalizeUrl(candidate, fallbackUrl);
      if (normalized && /\/i\/articles?\//i.test(normalized)) {
        return normalized;
      }
    }

    return fallbackUrl || "";
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

  function _cleanLine(text) {
    return (text || "").replace(/\s+/g, " ").trim();
  }

  function _unique(lines, max = 200) {
    const out = [];
    const seen = new Set();
    for (const raw of lines || []) {
      const line = _cleanLine(raw);
      if (!line) {
        continue;
      }
      const key = line.toLowerCase();
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      out.push(line);
      if (out.length >= max) {
        break;
      }
    }
    return out;
  }

  function _looksLikeUiChrome(line) {
    if (!line) {
      return true;
    }
    const lower = line.toLowerCase();
    const blacklist = [
      "post",
      "reply",
      "reposts",
      "likes",
      "bookmarks",
      "share",
      "follow",
      "following",
      "for you",
      "what's happening",
      "trending",
      "home",
      "messages",
      "profile",
      "more",
    ];
    return blacklist.some((word) => lower === word);
  }

  function _looksLikeProfileOrNav(line) {
    if (!line) {
      return true;
    }
    const lower = line.toLowerCase();
    const patterns = [
      /\bfollowers?\b/,
      /\bfollowing\b/,
      /\bjoined\b/,
      /\bview profile\b/,
      /\bprofile\b/,
      /\bposts?\b/,
      /\breposts?\b/,
      /\bmedia\b/,
      /\blikes\b/,
      /\bsubscribe\b/,
      /\bmessage\b/,
      /\bwho to follow\b/,
      /\btrending\b/,
      /^@[\w_]{1,20}$/,
    ];
    return patterns.some((pattern) => pattern.test(lower));
  }

  function _readMeta(doc, selector, attr = "content") {
    return _cleanLine(doc.querySelector(selector)?.getAttribute(attr) || "");
  }

  function _extractArticleTitle(doc) {
    const fromNodes = [
      _cleanLine(doc.querySelector("h1[data-testid='tweetText']")?.textContent || ""),
      _cleanLine(doc.querySelector("main h1")?.textContent || ""),
      _cleanLine(doc.querySelector("article h1")?.textContent || ""),
      _cleanLine(doc.querySelector("h1")?.textContent || ""),
    ].filter(Boolean);

    if (fromNodes.length) {
      return fromNodes[0];
    }

    const fromMeta = [
      _readMeta(doc, "meta[property='og:title']"),
      _readMeta(doc, "meta[name='twitter:title']"),
      _cleanLine((doc.title || "").replace(/\s*\/\s*X\s*$/i, "")),
    ].filter(Boolean);

    return fromMeta[0] || "";
  }

  function _resolveArticleRoot(doc) {
    const titleNode =
      doc.querySelector("h1[data-testid='tweetText']") ||
      doc.querySelector("main h1") ||
      doc.querySelector("article h1") ||
      doc.querySelector("h1");
    if (!titleNode) {
      return doc.querySelector("main") || doc.querySelector("article") || doc.body;
    }

    const main = titleNode.closest("main");
    if (main) {
      return main;
    }

    return titleNode.closest("article, section, div") || doc.body;
  }

  function _extractFromTextBlocks(root) {
    const containers = Array.from(root.querySelectorAll("article, section, div"));
    const lines = [];
    for (const el of containers) {
      const txt = _cleanLine(el.textContent || "");
      if (txt.length >= 200 && !_looksLikeUiChrome(txt) && !_looksLikeProfileOrNav(txt)) {
        lines.push(txt);
      }
      if (lines.length >= 40) {
        break;
      }
    }
    return lines;
  }

  function _extractArticleLines(doc) {
    const root = _resolveArticleRoot(doc);
    const selectors = [
      "[data-testid='articleBody'] p",
      "[data-testid='articleBody'] div[dir='auto']",
      "article [data-testid='tweetText']",
      "[data-testid='tweetText']",
      "article p",
      "p",
    ];

    const collected = [];
    for (const selector of selectors) {
      const lines = Array.from(root.querySelectorAll(selector))
        .map((el) => _cleanLine(el.textContent))
        .filter((line) => line.length > 30 && !_looksLikeUiChrome(line) && !_looksLikeProfileOrNav(line));
      if (lines.length) {
        collected.push(...lines);
      }
    }

    if (collected.length) {
      const unique = _unique(collected);
      if (unique.length >= 2 || unique.join(" ").length >= 140) {
        return unique.slice(0, 240);
      }
    }

    const blockLines = _unique(_extractFromTextBlocks(root));
    if (blockLines.length) {
      return blockLines.slice(0, 120);
    }

    const articleRoot = root.querySelector("article") || root;
    if (!articleRoot) {
      return [];
    }

    const fallback = _cleanLine(articleRoot.textContent);
    if (!fallback) {
      return [];
    }

    return fallback
      .split(/(?<=[.!?])\s+/)
      .map((line) => _cleanLine(line))
      .filter((line) => line.length > 30 && !_looksLikeUiChrome(line) && !_looksLikeProfileOrNav(line))
      .slice(0, 120);
  }

  function extractArticle(doc, pageUrl) {
    const title = _extractArticleTitle(doc) || "Untitled X Article";

    const lines = _extractArticleLines(doc);
    let text = lines.join("\n").trim();
    if (!text) {
      const bodyFallback = _cleanLine(doc.body?.textContent || "");
      if (bodyFallback.length >= 80) {
        text = bodyFallback.slice(0, 20000);
      }
    }
    if (!text) {
      return null;
    }

    const bylineAnchor = Array.from(doc.querySelectorAll("a[href^='/'], a[href*='x.com/']")).find((anchor) => {
      const href = anchor.getAttribute("href") || "";
      return TOKEN_RE.test(href) || /x\.com\/[A-Za-z0-9_]{1,15}$/.test(anchor.href || "");
    });
    const authorHandle = bylineAnchor ? detectHandle(bylineAnchor.closest("article") || doc.body) : null;
    const authorName =
      _cleanLine(doc.querySelector("main [data-testid='User-Name'] span")?.textContent || "") || null;
    const createdAt = doc.querySelector("time")?.getAttribute("datetime") || null;
    const articleUrl = detectArticleUrl(doc, pageUrl);
    const articleId = parseArticleIdFromUrl(articleUrl) || parseArticleIdFromUrl(pageUrl);

    return {
      article_id: articleId,
      url: articleUrl || pageUrl,
      title,
      author_handle: authorHandle,
      author_name: authorName,
      created_at: createdAt,
      text,
      captured_at: new Date().toISOString(),
      json_raw: {
        source_kind: "article",
      },
    };
  }

  globalObject.XicCaptureCore = {
    collectVisibleTweets,
    detectArticleUrl,
    detectHandle,
    extractArticle,
    extractTweet,
    parseArticleIdFromUrl,
    parseTweetIdFromUrl,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);
