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
  ["#monthly-income-chart", element()],
  ["#portfolio-drift", element()],
  ["#home-performance", element()],
  ["#net-invested", element()],
  ["#capital-applied-note", element()],
]);
const dashboard = {
  portfolio: { cash: 0, total_cost: 0, total_market_value: 0, total_result: 0, portfolio_equity: 0, total_contributions: 0, total_withdrawals: 0, net_external_flow: 0, capital_applied: 0, capital_applied_status: "ZERO", realized_result: 0, unrealized_result: 0, income_received: 0 },
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
  console, financialConcepts:{returnTooltip:"TWR"}, setupPortfolioView() {}, updatePortfolioView() {},
  document,
  portfolioApi: { dashboard: async () => dashboard, operations: async () => ({ operations: [] }) },
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
assert.match(nodes.get("#positions").innerHTML, /Seus investimentos aparecerão aqui/);
assert.equal(nodes.get("#class-allocation").innerHTML, "Composição indisponível");
assert.equal(nodes.get("#net-invested").textContent, "R$ 0");
assert.match(nodes.get("#capital-applied-note").textContent, /Não há posições abertas/);
assert(!nodes.get("#portfolio-evolution").innerHTML.includes("Carregando"));
assert.equal(title.textContent, "Seus investimentos, em um só lugar");

assert.ok(source.includes('selector === "#positions" ? holdingsSkeleton : loadingState'));
assert.match(source, /if \(dashboardTarget\) dashboardTarget\.innerHTML = content/);
assert.match(source, /if \(legacyStrategyTarget\) \{/);
console.log("Portfolio loading regression checks passed.");

// A failed request for a new wallet must not retain the prior wallet's figures.
for (const id of ['equity','home-return','income']) nodes.set(`#${id}`,element());
const insight=element();insight.hidden=false;insight.textContent='Previous wallet';nodes.set('#portfolio-insight',insight);
let rejectDashboard;
context.portfolioApi.dashboard=()=>new Promise((_resolve,reject)=>{rejectDashboard=reject;});
const failedLoad=context.loadPortfolio();
assert.equal(nodes.get('#equity').textContent,'Carregando…');assert.equal(insight.hidden,true);assert.equal(insight.textContent,'');
assert.equal(nodes.get('#monthly-income-chart').innerHTML,'Carregando…');
rejectDashboard(new Error('offline'));await failedLoad;
for (const id of ['equity','home-return','income','net-invested']) assert.equal(nodes.get(`#${id}`).textContent,'Indisponível');
assert.match(nodes.get('#monthly-income-chart').innerHTML,/offline/);
console.log('Failed wallet refresh clears prior metrics, monthly income and insight.');

// A delayed previous request cannot overwrite the most recently selected wallet.
const pending=[];context.portfolioApi.dashboard=()=>new Promise(resolve=>pending.push(resolve));
const older=context.loadPortfolio();const newer=context.loadPortfolio();
pending[1]({...dashboard,portfolio:{...dashboard.portfolio,capital_applied_status:'AVAILABLE',capital_applied:222}});await newer;
pending[0]({...dashboard,portfolio:{...dashboard.portfolio,capital_applied_status:'AVAILABLE',capital_applied:111}});await older;
assert.equal(nodes.get('#net-invested').textContent,'R$ 222');
console.log('Rapid wallet refresh: delayed older response cannot overwrite the current wallet.');
