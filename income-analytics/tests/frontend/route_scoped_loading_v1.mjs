import assert from "node:assert/strict";
import fs from "node:fs";

const lifecycleSource = fs.readFileSync(
  "src/income_analytics/api/static/js/shared/route-lifecycle.js",
  "utf8",
);
const lifecycleModule = await import(
  `data:text/javascript;charset=utf-8,${encodeURIComponent(lifecycleSource)}`
);
const { createRouteLifecycle, createRouteResource } = lifecycleModule;

let calls = [];
const request = endpoint => {
  calls.push(endpoint);
  return Promise.resolve(endpoint);
};
const intelligence = createRouteResource(() => request("intelligence"));
const routes = createRouteLifecycle({
  beginCycle: () => intelligence.invalidate(),
  globalLoader: () => intelligence.read(),
  loaders: {
    "minha-carteira": () => request("dashboard"),
    entender: () => Promise.all([request("wealth-explanation"), request("wealth-evolution")]),
    estrategia: () => Promise.all([request("holdings"), intelligence.read()]),
    simular: () => request("allocation-analysis"),
    operacoes: () => Promise.all([request("operations-history"), request("recurring-rules")]),
  },
});

const expected = {
  "minha-carteira": ["dashboard", "intelligence"],
  entender: ["intelligence", "wealth-evolution", "wealth-explanation"],
  estrategia: ["holdings", "intelligence"],
  simular: ["allocation-analysis", "intelligence"],
  operacoes: ["intelligence", "operations-history", "recurring-rules"],
};

for (const [route, endpoints] of Object.entries(expected)) {
  calls = [];
  const result = await routes.activate(route);
  assert(result.results.every(item => item.status === "fulfilled"));
  assert.deepEqual([...calls].sort(), [...endpoints].sort(), route);
  assert.equal(new Set(calls).size, calls.length, `duplicate request on ${route}`);
}

calls = [];
const isolatedResource = createRouteResource(() => request("intelligence"));
await isolatedResource.read();
await isolatedResource.read();
assert.deepEqual(calls, ["intelligence"]);
isolatedResource.invalidate();
await isolatedResource.read();
assert.deepEqual(calls, ["intelligence", "intelligence"]);

let recovered = false;
const isolated = createRouteLifecycle({
  loaders: {
    broken: () => Promise.reject(new Error("expected")),
    healthy: () => { recovered = true; },
  },
});
const failure = await isolated.activate("broken");
assert.equal(failure.results[1].status, "rejected");
await isolated.activate("healthy");
assert.equal(recovered, true);

const app = fs.readFileSync("src/income_analytics/api/static/js/app.js", "utf8");
const performance = fs.readFileSync("src/income_analytics/api/static/js/features/performance.js", "utf8");
const operations = fs.readFileSync("src/income_analytics/api/static/js/features/operations.js", "utf8");
const portfolio = fs.readFileSync("src/income_analytics/api/static/js/features/portfolio.js", "utf8");
const tools = fs.readFileSync("src/income_analytics/api/static/js/features/tools.js", "utf8");

assert.match(app, /const routeLoaders =/);
assert.match(app, /createRouteLifecycle/);
assert.doesNotMatch(app, /initialize\("operações"/);
assert.match(performance, /if \(performanceBound\) return/);
assert.match(performance, /renderAnalysisAnswer\(contributionData\)/);
assert.match(performance, /renderQuestionChoices\(\)/);
assert.doesNotMatch(performance, /understandChart|loadECharts/);
assert.match(operations, /if \(!form \|\| operationsBound\) return/);
assert.match(portfolio, /if \(portfolioFiltersBound\) return/);
assert.match(portfolio, /refreshAttention = true/);
assert.match(tools, /if \(toolsSetup\) return/);

console.log("Route scoped frontend loading V1 checks passed.");
