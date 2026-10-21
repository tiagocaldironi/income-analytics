import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/portfolio.js", "utf8");
source = source.replace(/^import .*;\r?\n/gm, "").replaceAll("export async function", "async function").replaceAll("export function", "function");
source += "\nglobalThis.__aggregateMonthlyIncome = aggregateMonthlyIncome;";
const context = vm.createContext({});
vm.runInContext(source, context);

const { months, byCurrency } = context.__aggregateMonthlyIncome([
  { type: "DIVIDEND", effective_date: "2025-10-02", amount: 20, currency_code: "BRL" },
  { type: "INTEREST_ON_EQUITY", effective_date: "2025-10-18", amount: 5, currency_code: "BRL" },
  { type: "FII_INCOME", effective_date: "2026-10-01", amount: 2, currency_code: "USD" },
  { type: "DEPOSIT", effective_date: "2026-10-02", amount: 1000, currency_code: "BRL" },
  { type: "BUY", effective_date: "2026-10-03", amount: 100, currency_code: "BRL" },
  { type: "DIVIDEND", effective_date: "2025-09-30", amount: 50, currency_code: "BRL" },
], new Date(2026, 9, 21));

assert.equal(months.length, 12);
assert.equal(months[0].key, "2025-11");
assert.equal(months.at(-1).key, "2026-10");
assert.equal(byCurrency.has("BRL"), false);
assert.equal(byCurrency.get("USD")["2026-10"], 2);

const multiCurrency = context.__aggregateMonthlyIncome([
  { type: "DIVIDEND", effective_date: "2025-11-01", amount: 20, currency_code: "BRL" },
  { type: "INTEREST_ON_EQUITY", effective_date: "2025-11-18", amount: 5, currency_code: "BRL" },
  { type: "FII_INCOME", effective_date: "2025-11-28", amount: 2, currency_code: "USD" },
], new Date(2026, 9, 21));
assert.equal(multiCurrency.byCurrency.get("BRL")["2025-11"], 25);
assert.equal(multiCurrency.byCurrency.get("USD")["2025-11"], 2);
assert.equal(multiCurrency.byCurrency.get("BRL")["2026-10"], 0);

console.log("Portfolio redesign income history groups real receipts by month and keeps currencies separate.");
