import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/performance.js", "utf8");
source = source.replace(/^import .*;\r?\n/gm, "").replaceAll("export async function", "async function").replaceAll("export function", "function");
source += "\nglobalThis.__buildContributionRows = buildContributionRows;";
const context = vm.createContext({});
vm.runInContext(source, context);

const rows = context.__buildContributionRows({
  components: [
    { component_type: "MARKET_VALUATION", children: [
      { ticker: "PETR4", asset_class: "BRAZILIAN_STOCK", signed_amount: 20, valuation_available: true },
      { ticker: "VALE3", asset_class: "BRAZILIAN_STOCK", signed_amount: -8, valuation_available: false },
    ] },
    { component_type: "NET_ACQUISITIONS", children: [
      { ticker: "PETR4", asset_class: "BRAZILIAN_STOCK", signed_amount: 100, valuation_available: true },
    ] },
    { component_type: "UNEXPLAINED", signed_amount: -3, children: [] },
  ],
  income_generated: { items: [
    { ticker: "PETR4", asset_class: "BRAZILIAN_STOCK", signed_amount: 5 },
    { ticker: "HGLG11", asset_class: "FII", signed_amount: 4 },
  ] },
});

assert.equal(rows.length, 3);
assert.equal(rows.find(row => row.ticker === "PETR4").value, 25);
assert.equal(rows.find(row => row.ticker === "VALE3").value, -8);
assert.equal(rows.find(row => row.ticker === "VALE3").valuation_available, false);
assert.equal(rows.find(row => row.ticker === "HGLG11").value, 4);
console.log("Contribution attribution combines asset valuation and paid income while excluding capital flows.");
