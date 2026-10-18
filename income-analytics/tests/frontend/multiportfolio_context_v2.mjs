import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const pending = [];
const storage = new Map([["income.activePortfolioId", "portfolio-a"]]);
const localStorage = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, String(value)),
};
const source = fs.readFileSync("src/income_analytics/api/static/js/api.js", "utf8")
  .replace(/^export const /gm, "const ") + "\nglobalThis.portfolioApi = portfolioApi;";
const context = vm.createContext({
  AbortController,
  DOMException,
  Headers,
  URLSearchParams,
  performance: { now: () => 0, measure() {} },
  window: { localStorage, setTimeout, clearTimeout },
  fetch: (url, options) => new Promise(resolve => pending.push({ url, options, resolve })),
});
vm.runInContext(source, context);

const staleRequest = context.portfolioApi.portfolio();
assert.equal(pending[0].options.headers.get("X-Portfolio-Id"), "portfolio-a");
localStorage.setItem("income.activePortfolioId", "portfolio-b");
pending[0].resolve({
  ok: true,
  json: async () => ({ positions: [{ ticker: "A_ONLY" }] }),
});
await assert.rejects(staleRequest, error => error.name === "AbortError");

const bRequest = context.portfolioApi.portfolio();
assert.equal(pending[1].options.headers.get("X-Portfolio-Id"), "portfolio-b");
pending[1].resolve({ ok: true, json: async () => ({ positions: [] }) });
assert.deepEqual(await bRequest, { positions: [] });
