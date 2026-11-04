import assert from "node:assert/strict";
import fs from "node:fs";

const code = fs.readFileSync("src/income_analytics/api/static/js/shared/dashboard-refresh.js", "utf8");
const { waitForDashboard } = await import("data:text/javascript;base64," + Buffer.from(code).toString("base64"));
const states = ["UPDATING", "UPDATING", "VALID"];
const waits = [];
assert.equal(await waitForDashboard({
  status: async () => ({ status: states.shift(), portfolio_id: "a" }),
  portfolioId: "a", isCurrent: () => true, pause: async ms => waits.push(ms),
}), "VALID");
assert.deepEqual(waits, [1000, 1000]);

let calls = 0;
assert.equal(await waitForDashboard({
  status: async () => { calls++; }, isCurrent: () => false,
}), "CANCELLED");
assert.equal(calls, 0);
let current = true;
assert.equal(await waitForDashboard({
  status: async () => { current = false; return { status: "VALID" }; },
  isCurrent: () => current,
}), "CANCELLED");

await assert.rejects(waitForDashboard({
  status: async () => ({ status: "VALID", portfolio_id: "b" }),
  portfolioId: "a", isCurrent: () => true,
}), /carteira mudou/);
for (const status of ["ERROR", "MISSING"]) {
  await assert.rejects(waitForDashboard({
    status: async () => ({ status }), isCurrent: () => true,
  }), /excluído.*recálculo/);
}
calls = 0;
await assert.rejects(waitForDashboard({
  status: async () => { calls++; return { status: "UPDATING" }; },
  isCurrent: () => true, pause: async () => {}, attempts: 3,
}), /continua em andamento/);
assert.equal(calls, 3);
await assert.rejects(waitForDashboard({
  status: async () => { throw new Error("Offline"); }, isCurrent: () => true,
}), /Offline/);
console.log("Dashboard refresh: ready, pending, cancellation, wallet isolation, errors and bounded polling PASS.");
