import fs from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/portfolio.js", "utf8");
source = source.replace(/^import .*;\r?\n/gm, "").replaceAll("export async function", "async function").replaceAll("export function", "function");
const context = vm.createContext({});
vm.runInContext(source, context);

const targetOnly = {
  target_only: true,
  name: "TURBO",
  contract_label: "TURBO · RDB · CDI · 120% do CDI",
  target_weight: 0.5,
};
const heldLot = {
  target_only: false,
  name: "CDB NUCLE",
  contract_key: "NUCLE|CDB|CDI|120",
  contract_label: "NUCLE · CDB · CDI · 120% do CDI",
  quantity: 1,
  average_price: 500,
  market_value: 525,
  total_result: 25,
  income_received: 0,
};
const displayed = context.assetsForDisplay({
  asset_class: "FIXED_INCOME",
  assets: [targetOnly, heldLot],
});
assert.equal(displayed.length, 1);
assert.equal(displayed[0].display_name, heldLot.contract_label);
assert.equal(displayed[0].lot_count, 1);
assert.equal(context.assetsForDisplay({ asset_class: "BRAZILIAN_STOCK", assets: [targetOnly, heldLot] }).length, 1);
console.log("Target-only assets are excluded from the holdings rows.");
