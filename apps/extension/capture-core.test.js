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
});
