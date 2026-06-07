import { readFileSync } from "node:fs";
import path from "node:path";
import vm from "node:vm";

import { beforeAll, describe, expect, it } from "vitest";

beforeAll(() => {
  const source = readFileSync(path.join(process.cwd(), "settings-core.js"), "utf8");
  vm.runInThisContext(source, { filename: "settings-core.js" });
});

function storageArea(initial = {}) {
  const values = { ...initial };
  return {
    values,
    async get(keys) {
      return Object.fromEntries(keys.filter((key) => key in values).map((key) => [key, values[key]]));
    },
    async set(next) {
      Object.assign(values, next);
    },
    async remove(keys) {
      for (const key of keys) {
        delete values[key];
      }
    },
  };
}

describe("settings-core", () => {
  it("allows HTTPS and local HTTP API bases only", () => {
    const api = globalThis.XicSettingsCore;

    expect(api.normalizeApiBase("https://api.example.com/")).toBe("https://api.example.com");
    expect(api.normalizeApiBase("http://localhost:8000/")).toBe("http://localhost:8000");
    expect(() => api.normalizeApiBase("http://api.example.com")).toThrow(/must use HTTPS/);
    expect(() => api.normalizeApiBase("https://user:pass@api.example.com")).toThrow(/cannot include credentials/);
  });

  it("validates PAT format and creates exact permission origins", () => {
    const api = globalThis.XicSettingsCore;
    const pat = "xic_pat_abcDEF123_-abcdefghijklmnopqrst";

    expect(api.validatePat(pat)).toBe(pat);
    expect(api.permissionOrigin("https://api.example.com/v1")).toBe("https://api.example.com/*");
    expect(() => api.validatePat("xic_pat_short")).toThrow(/valid PAT/);
  });

  it("migrates legacy sync settings into local storage", async () => {
    const api = globalThis.XicSettingsCore;
    const local = storageArea();
    const sync = storageArea({
      xic_pat: "xic_pat_abcDEF123_-abcdefghijklmnopqrst",
      xic_api_base: "https://api.example.com",
    });

    const settings = await api.readSettings({ storage: { local, sync } });

    expect(settings.apiBase).toBe("https://api.example.com");
    expect(local.values.xic_pat).toBe(settings.pat);
    expect(sync.values).toEqual({});
  });

  it("returns actionable authentication and CORS errors", () => {
    const api = globalThis.XicSettingsCore;

    expect(api.apiErrorMessage(401, {})).toMatch(/new extension PAT/);
    expect(api.apiErrorMessage(403, {})).toMatch(/extension ID/);
  });
});
