import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/portfolio.js", "utf8");
source = source.replace(/^import .*;\r?\n/gm, "").replaceAll("export async function", "async function").replaceAll("export function", "function");

const element = () => ({
  innerHTML: "",
  textContent: "",
  classList: { add() {} },
  closest() { return null; },
  querySelector() { return null; },
  insertAdjacentHTML() {},
});
const title = element();
const card = { classList: { add() {} }, querySelector: selector => selector === "h2" ? title : null };
const positions = element();
positions.closest = () => card;
const nodes = new Map([
  ["#positions", positions],
  ["#understand-history", element()],
  ["#class-allocation", element()],
  ["#portfolio-evolution", element()],
  ["#portfolio-drift", element()],
  ["#home-performance", element()],
]);
const dashboard = {
  portfolio: { cash: 0, total_cost: 0, total_market_value: 0, total_result: 0, portfolio_equity: 0, total_contributions: 0, total_withdrawals: 0, realized_result: 0, unrealized_result: 0, income_received: 0 },
  performance: null,
  history: { snapshots: [], period_months: 12, asset_class: "" },
  allocation: { assets: [] },
  class_allocation: [],
  holdings: { base_currency: "BRL", classes: [], portfolio_drift: 0 },
};
const document = {
  querySelector: selector => nodes.get(selector) || null,
  dispatchEvent() {},
  addEventListener() {},
};
const context = vm.createContext({
  console,
  document,
  portfolioApi: { dashboard: async () => dashboard },
  loadingState: "Carregando…",
  errorState: message => `Erro: ${message}`,
  emptyState: message => message,
  money: value => `R$ ${value}`,
  percentage: value => `${value}%`,
  table: (_headers, rows) => rows.join(""),
  Event,
  ResizeObserver: class { observe() {} disconnect() {} },
  requestAnimationFrame: callback => callback(),
});
vm.runInContext(source, context);

// The current page intentionally has no #allocation or
// #strategy-class-allocation. Their absence must not stop the dashboard.
await context.loadPortfolio();
assert.match(nodes.get("#positions").innerHTML, /Sua carteira ainda está vazia/);
assert.equal(nodes.get("#class-allocation").innerHTML, "Nenhuma posição disponível.");
assert(!nodes.get("#portfolio-evolution").innerHTML.includes("Carregando"));
assert.equal(title.textContent, "Meus ativos");

assert.match(source, /if \(container\) container\.innerHTML = loadingState/);
assert.match(source, /if \(dashboardTarget\) dashboardTarget\.innerHTML = content/);
assert.match(source, /if \(legacyStrategyTarget\) legacyStrategyTarget\.innerHTML = content/);
console.log("Portfolio loading regression checks passed.");
