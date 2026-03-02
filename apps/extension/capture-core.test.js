// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import path from "node:path";
import vm from "node:vm";

import { beforeAll, describe, expect, it } from "vitest";

beforeAll(() => {
  const source = readFileSync(path.join(process.cwd(), "capture-core.js"), "utf8");
  vm.runInThisContext(source, { filename: "capture-core.js" });
});

describe("capture-core", () => {
  it("extracts tweet content and quoted tweet metadata", () => {
    document.body.innerHTML = `
      <article data-testid="tweet">
        <a href="/alice/status/12345"></a>
        <a href="/bob/status/98765"></a>
        <a href="/alice">alice</a>
        <div data-testid="User-Name"><span>Alice</span></div>
        <div data-testid="tweetText">Main tweet text</div>
        <div data-testid="tweetText">Quoted tweet text</div>
      </article>
    `;

    const api = globalThis.XicCaptureCore;
    const article = document.querySelector("article[data-testid='tweet']");
    const tweet = api.extractTweet(article);

    expect(tweet).toBeTruthy();
    expect(tweet.tweet_id).toBe("12345");
    expect(tweet.author_handle).toBe("alice");
    expect(tweet.text).toContain("Main tweet text");
    expect(tweet.quoted).toBeTruthy();
    expect(tweet.quoted.tweet_id).toBe("98765");
    expect(tweet.quoted.text).toBe("Quoted tweet text");
  });

  it("collects visible tweets from the document", () => {
    document.body.innerHTML = `
      <article data-testid="tweet">
        <a href="/alice/status/111"></a>
        <a href="/alice">alice</a>
        <div data-testid="User-Name"><span>Alice</span></div>
        <div data-testid="tweetText">one</div>
      </article>
      <article data-testid="tweet">
        <a href="/bob/status/222"></a>
        <a href="/bob">bob</a>
        <div data-testid="User-Name"><span>Bob</span></div>
        <div data-testid="tweetText">two</div>
      </article>
    `;

    const api = globalThis.XicCaptureCore;
    const tweets = api.collectVisibleTweets(document);

    expect(tweets).toHaveLength(2);
    expect(tweets.map((t) => t.tweet_id)).toEqual(["111", "222"]);
  });

  it("extracts article content from an X article page", () => {
    document.body.innerHTML = `
      <main>
        <h1>HBM Capacity Deep Dive</h1>
        <article>
          <p>HBM supply remains constrained due to packaging bottlenecks.</p>
          <p>Vendors are expanding capacity but demand still outpaces output.</p>
        </article>
      </main>
    `;

    const api = globalThis.XicCaptureCore;
    const article = api.extractArticle(document, "https://x.com/i/article/abc123xyz");

    expect(article).toBeTruthy();
    expect(article.article_id).toBe("abc123xyz");
    expect(article.title).toBe("HBM Capacity Deep Dive");
    expect(article.text).toContain("HBM supply remains constrained");
    expect(article.url).toBe("https://x.com/i/article/abc123xyz");
  });

  it("extracts article using canonical URL when page URL is not /i/article", () => {
    document.body.innerHTML = `
      <link rel="canonical" href="https://x.com/i/articles/xyz_789" />
      <main>
        <h1>Photonics Roadmap</h1>
        <article>
          <p>CPO adoption may accelerate with AI cluster power constraints.</p>
          <p>Packaging ecosystem maturity remains a gating factor.</p>
        </article>
      </main>
    `;

    const api = globalThis.XicCaptureCore;
    const article = api.extractArticle(document, "https://x.com/someuser/status/123");

    expect(article).toBeTruthy();
    expect(article.article_id).toBe("xyz_789");
    expect(article.url).toBe("https://x.com/i/articles/xyz_789");
  });

  it("falls back to meta title and main text blocks", () => {
    document.body.innerHTML = `
      <meta property="og:title" content="AI Infra Supply Chain 2026" />
      <main>
        <section>
          Manufacturing updates suggest memory and packaging constraints are improving, while power and cooling remain structural bottlenecks for cluster rollout.
        </section>
      </main>
    `;

    const api = globalThis.XicCaptureCore;
    const article = api.extractArticle(document, "https://x.com/i/articles/meta_001");

    expect(article).toBeTruthy();
    expect(article.title).toBe("AI Infra Supply Chain 2026");
    expect(article.text).toContain("Manufacturing updates suggest memory and packaging constraints");
  });

  it("prefers article body over profile description text", () => {
    document.body.innerHTML = `
      <main>
        <h1>HBM TAM Outlook</h1>
        <section>
          <div data-testid="UserDescription">
            Investor writing about semis and AI. 120K followers. Following 240. Joined 2018.
          </div>
        </section>
        <article>
          <p>HBM capacity is expanding but packaging and test remain gating factors through 2026.</p>
          <p>Memory pricing upside depends on sustained AI demand and customer qualification timelines.</p>
        </article>
      </main>
    `;

    const api = globalThis.XicCaptureCore;
    const article = api.extractArticle(document, "https://x.com/i/articles/hbm_2026");

    expect(article).toBeTruthy();
    expect(article.text).toContain("HBM capacity is expanding");
    expect(article.text).not.toContain("120K followers");
  });
});
