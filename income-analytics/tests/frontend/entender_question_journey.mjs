import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/performance.js", "utf8");
source = source.replace(/^import .*;\r?\n/gm, "").replaceAll("export async function", "async function").replaceAll("export function", "function");
source += "\nglobalThis.__buildContributionRows = buildContributionRows; globalThis.__filterAndSortContributions = filterAndSortContributions; globalThis.__analyses = understandAnalyses;";
const context = vm.createContext({});
vm.runInContext(source, context);

const rows = context.__buildContributionRows({
  components: [
    { component_type: "MARKET_VALUATION", children: [
      { ticker: "WEGE3", label: "WEG", asset_class: "BRAZILIAN_STOCK", signed_amount: 42, valuation_available: true },
      { ticker: "PETR4", label: "Petrobras", asset_class: "BRAZILIAN_STOCK", signed_amount: -42, valuation_available: true },
      { ticker: "ITSA4", label: "Itaúsa", asset_class: "BRAZILIAN_STOCK", signed_amount: 12, valuation_available: true },
      { ticker: "BBDC4", label: "Bradesco", asset_class: "BRAZILIAN_STOCK", signed_amount: -9, valuation_available: true },
      { ticker: "ABEV3", label: "Ambev", asset_class: "BRAZILIAN_STOCK", signed_amount: 100, valuation_available: false },
    ] },
    { component_type: "NET_ACQUISITIONS", children: [
      { ticker: "WEGE3", asset_class: "BRAZILIAN_STOCK", signed_amount: 500, valuation_available: true },
    ] },
  ],
  income_generated: { items: [{ ticker: "WEGE3", label: "WEG", asset_class: "BRAZILIAN_STOCK", signed_amount: 3, event_type: "DIVIDEND" }] },
});

assert.equal(rows.find(row => row.ticker === "WEGE3").value, 45, "income is included while the capital flow is excluded");
assert.equal(rows.find(row => row.ticker === "ABEV3").contribution_available, false, "unvalued rows stay unavailable, not zero");
assert.deepEqual(Array.from(context.__filterAndSortContributions(rows, "GAINS"), row => row.ticker), ["WEGE3", "ITSA4"]);
assert.deepEqual(Array.from(context.__filterAndSortContributions(rows, "LOSSES"), row => row.ticker), ["PETR4", "BBDC4"]);
assert.deepEqual(Array.from(context.__filterAndSortContributions(rows, "ALL"), row => row.ticker), ["WEGE3", "PETR4", "ITSA4", "BBDC4"]);
assert.deepEqual(Array.from(context.__filterAndSortContributions(rows, "ALL", "FII"), row => row.ticker), []);
assert.deepEqual(Array.from(context.__analyses, item => item.id), ["asset-contributions", "wealth-bridge", "paid-income", "fixed-income"]);
console.log("Entender: question catalog, financial row attribution, class filters, gain/loss filters, and deterministic ranking passed.");
