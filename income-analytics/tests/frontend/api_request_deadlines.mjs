import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("src/income_analytics/api/static/js/api.js", "utf8");
const requestSource = source.slice(source.indexOf("async function request("), source.indexOf("export const portfolioApi"));
let wallet = "wallet-a", csrfCalls = 0, fetchCalls = 0, timer, duration;
let fetchImpl = async () => ({ ok: true, json: async () => ({ saved: true }) });
const context = vm.createContext({
  AbortController, DOMException, Headers, performance,
  refreshCsrf: async () => { csrfCalls++; assert.equal(timer, undefined); return "csrf"; },
  fetch: async (...args) => { fetchCalls++; return fetchImpl(...args); },
  window: {
    localStorage: { getItem: () => wallet },
    sessionStorage: { getItem: () => "user" },
    setTimeout: (callback, ms) => { timer = callback; duration = ms; return 1; },
    clearTimeout: () => { timer = undefined; },
  },
});
vm.runInContext(requestSource, context);
assert.equal((await context.request("/trades", { method: "POST" })).saved, true);
assert.equal(duration, 120000);
assert.equal(csrfCalls, 1);
await context.request("/market-prices/refresh", { method: "POST" });
assert.equal(duration, 180000);
await context.request("/portfolio");
assert.equal(duration, 30000);

// A slow write remains pending after the former 15-second deadline, with no retry.
fetchImpl = async (_, options) => {
  assert.equal(options.headers.get("X-CSRF-Token"), "csrf");
  return new Promise((resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(options.signal.reason), { once: true });
  });
};
const before = fetchCalls;
const slowWrite = context.request("/trades", { method: "POST" });
await new Promise(resolve => setImmediate(resolve));
assert.equal(duration, 120000);
timer();
await assert.rejects(slowWrite, /pode ter sido concluída.*histórico/);
assert.equal(fetchCalls, before + 1);
assert.equal(timer, undefined);

// Deadline covers body parsing too: an aborted response cannot become an empty success.
fetchImpl = async () => ({ ok: true, json: async () => { timer(); throw new DOMException("aborted", "AbortError"); } });
await assert.rejects(context.request("/portfolio"), /demorou para responder/);

// Caller cancellation composes with, rather than replaces, the deadline.
const caller = new AbortController();
fetchImpl = async (_, options) => {
  caller.abort(new DOMException("Caller cancelled", "AbortError"));
  throw options.signal.reason;
};
await assert.rejects(context.request("/portfolio", { signal: caller.signal }), /Caller cancelled/);
assert.equal(timer, undefined);

fetchImpl = async () => { wallet = "wallet-b"; return { ok: true, json: async () => ({}) }; };
await assert.rejects(context.request("/portfolio"), /carteira ativa mudou/);
console.log("API deadlines: writes, providers, CSRF, body abort, caller abort and wallet isolation passed.");
