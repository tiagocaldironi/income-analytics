import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

// Execute the real session exchange/logout client against a tiny HTTP double.
// Persistence assertions detect accidental bearer/refresh token storage.
const writes = [];
const map = new Map([["income.activePortfolioId", "old-wallet"]]);
const storage = {
  getItem: key => map.get(key) ?? null,
  setItem: (key, value) => { writes.push([key, value]); map.set(key, value); },
  removeItem: key => map.delete(key),
};
const calls = [];
let redirected;
const context = vm.createContext({
  Headers, localStorage: storage, sessionStorage: storage,
  location: { replace: value => { redirected = value; } },
  fetch: async (url, options) => {
    calls.push({ url, options });
    const body = url.endsWith("/csrf") ? { csrf_token: "csrf-server-value" }
      : url.endsWith("/session") ? { user_id: "internal-user", plan: "FREE" }
        : { signed_out: true };
    return { ok: true, json: async () => body };
  },
});
vm.runInContext(fs.readFileSync("src/income_analytics/api/static/js/auth-client.js", "utf8")
  .replace(/^export /gm, ""), context);
await context.exchangeSession({ getIdToken: async () => "DO-NOT-PERSIST-ID-TOKEN" });
assert.equal(calls.find(call => call.url.endsWith("/session")).options.headers.get("X-CSRF-Token"), "csrf-server-value");
assert.equal(JSON.parse(calls.find(call => call.url.endsWith("/session")).options.body).id_token, "DO-NOT-PERSIST-ID-TOKEN");
assert.equal(map.get("income.activePortfolioId"), undefined);
assert.ok(writes.every(([, value]) => value === "internal-user"));
assert.ok(!JSON.stringify(writes).includes("DO-NOT-PERSIST"));
await context.signOutDevice();
assert.equal(map.get("income.userId"), undefined);
assert.equal(map.get("income.authUser"), undefined);
assert.equal(redirected, "/entrar");
assert.ok(calls.every(call => call.options.credentials === "same-origin"));
console.log("Firebase BFF client: CSRF, memory-only token exchange and logout cleanup passed.");
