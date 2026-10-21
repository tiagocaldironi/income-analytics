import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/performance.js", "utf8");
source = source.replace(/^import .*;\r?\n/gm, "").replaceAll("export async function", "async function").replaceAll("export function", "function");
source += "\nglobalThis.__buildContributionRows = buildContributionRows; globalThis.__filterAndSortContributions = filterAndSortContributions; globalThis.__renderFixedIncomeAnswer = renderFixedIncomeAnswer; globalThis.__renderWealthBridgeAnswer = renderWealthBridgeAnswer; globalThis.__analyses = understandAnalyses;";
const context = vm.createContext({ money: value => String(value), percentage: value => `${value}%` });
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

const fixedIncomeAnswer = context.__renderFixedIncomeAnswer({
  base_currency: "BRL",
  bridge: { fixed_income_return: 20 },
  components: [{ component_type: "FIXED_INCOME_ACCRUAL", children: [
    { ticker: "CDB-A", label: "CDB A", asset_class: "FIXED_INCOME", signed_amount: 8, valuation_available: true },
    { ticker: "CDB-B", label: "CDB B", asset_class: "FIXED_INCOME", signed_amount: 21, valuation_available: true },
    { ticker: "CDB-C", label: "CDB C", asset_class: "FIXED_INCOME", signed_amount: -2, valuation_available: true },
  ] }],
});
assert.deepEqual(
  Array.from(fixedIncomeAnswer.matchAll(/class="ranking-position">(\d+)<\/span><span class="ranking-identity"><strong>([^<]+)/g), match => match[2]),
  ["CDB-B", "CDB-A", "CDB-C"],
  "fixed-income investments are ordered by highest to lowest accrued return amount",
);

const bridgeAnswer = context.__renderWealthBridgeAnswer({
  base_currency: "BRL",
  summary: { opening_wealth: 1000, closing_wealth: 950, absolute_change: -50 },
  data_quality: { explanation_coverage_percentage: 100, valuation_coverage_percentage: 100, unconverted_event_count: 0 },
  components: [{ component_type: "MARKET_VALUATION", label: "Valorização dos ativos", signed_amount: -50, children: [
    { ticker: "GAIN", signed_amount: 100 },
    { ticker: "LOSS", signed_amount: -150 },
  ] }],
  reconciliation: { unexplained_change: 0 },
});
assert.match(bridgeAnswer, /movement-up/);
assert.match(bridgeAnswer, /movement-down/);
assert.match(bridgeAnswer, /aria-label="Valorização negativa"/);
assert.match(bridgeAnswer, /<span>150<\/span>/, "negative valuation displays the absolute amount alongside its direction icon");
console.log("Entender: question catalog, financial row attribution, class and gain/loss filters, fixed-income return ranking, and valuation direction indicators passed.");
