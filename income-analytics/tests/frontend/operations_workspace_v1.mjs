import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/operations.js", "utf8");
source = source.replace(/^import .*;\r?\n/gm, "")
  .replaceAll("export async function", "async function")
  .replaceAll("export function", "function");
source += "\nglobalThis.__operationsTest = { operationsTabs, renderTimeline, renderHistoryFilters, renderOperationTypeGroup };";
const context = vm.createContext({
  money: (value, currency = "BRL") => currency + " " + Number(value).toFixed(2),
  emptyState: message => "<p>" + message + "</p>",
});
vm.runInContext(source, context);

const tabs = context.__operationsTest.operationsTabs;
tabs.get("MOVEMENTS").groups.set("BUY", { key: "BUY", label: "Compras", total: 306, items: [], hasMore: true, collapsed: false });
tabs.get("MOVEMENTS").groups.get("BUY").loaded = 20;
tabs.get("MOVEMENTS").filters.search = "PETR";
assert.equal(tabs.get("INCOME").groups.size, 0);
assert.equal(tabs.get("INCOME").filters.search, "");
assert.equal(tabs.get("ALL").items.length, 0);
const buyGroup = context.__operationsTest.renderOperationTypeGroup(tabs.get("MOVEMENTS").groups.get("BUY"));
assert.match(buyGroup, /Compras/);
assert.match(buyGroup, /306 lançamentos/);
assert.match(buyGroup, /Mostrando 0 de 306/);
assert.match(buyGroup, /Carregar mais/);

const html = context.__operationsTest.renderTimeline([
  { effective_date: "2026-09-25", registered_at: "2", ticker: "ITSA4", operation: "JCP", amount: 5, currency_code: "BRL", source: "Manual", event_type: "INTEREST_ON_EQUITY" },
  { effective_date: "2026-09-29", registered_at: "1", ticker: "PETR4", operation: "Compra", quantity: 2, unit_price: 30, amount: 60, currency_code: "BRL", source: "Manual", event_type: "BUY" },
]);
assert.match(html, /setembro de 2026/i);
assert.ok(html.indexOf("29/09/2026") < html.indexOf("25/09/2026"));
assert.match(html, /PETR4/);
assert.match(html, /ITSA4/);

const filters = context.__operationsTest.renderHistoryFilters(
  { period: "ALL", asset_class: "", event_type: "", search: "", start_date: "", end_date: "" },
  [{ key: "BRAZILIAN_STOCK", label: "Ações Brasil" }],
  "INCOME",
);
assert.match(filters, /Todos os rendimentos/);
assert.match(filters, /Dividendos/);
assert.match(filters, /Ações Brasil/);
console.log("Operations tabs and group state are independent; monthly timeline, group counts and income filters render.");
