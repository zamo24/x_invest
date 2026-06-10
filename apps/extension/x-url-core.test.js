import { readFileSync } from "node:fs";
import path from "node:path";
import vm from "node:vm";

import { beforeAll, describe, expect, it } from "vitest";

beforeAll(() => {
  vm.runInThisContext(readFileSync(path.join(process.cwd(), "x-url-core.js"), "utf8"));
});

describe("URL-only X capture", () => {
  it("sends only URL, folder ID, and mode", () => {
    expect(globalThis.XicXUrlCore.buildSavePayload("https://x.com/alice/status/123", "folder-1", "post")).toEqual({
      url: "https://x.com/alice/status/123",
      folder_id: "folder-1",
      mode: "post",
    });
  });

  it("rejects invalid, non-X, and article URLs", () => {
    for (const url of ["https://example.com/a/status/123", "https://x.com/home", "https://x.com/i/article/abc"]) {
      expect(() => globalThis.XicXUrlCore.validatePostUrl(url)).toThrow(/canonical x.com post URL/i);
    }
  });

  it("manifest has no X content scripts, scripting permission, or X host permission", () => {
    const manifest = JSON.parse(readFileSync(path.join(process.cwd(), "manifest.json"), "utf8"));
    expect(manifest.content_scripts).toBeUndefined();
    expect(manifest.permissions).not.toContain("scripting");
    expect(manifest.host_permissions || []).not.toContain("https://x.com/*");
  });

  it("contains no DOM extraction source files", () => {
    expect(() => readFileSync(path.join(process.cwd(), "capture-core.js"), "utf8")).toThrow();
    expect(() => readFileSync(path.join(process.cwd(), "content-script.js"), "utf8")).toThrow();
  });
});
