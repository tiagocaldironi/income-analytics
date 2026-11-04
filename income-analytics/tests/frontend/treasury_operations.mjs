import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/operations.js", "utf8")
  .replace(/^import .*;\r?\n/gm, "")
  .replaceAll("export async function", "async function").replaceAll("export function", "function");
const fields = new Map();
const node = selector => {
  if (!fields.has(selector)) fields.set(selector, {id: selector.slice(1), value: "", style: {},
    previousElementSibling: {hidden: false}, parent: {hidden: false},
    closest() { return this.parent; }, querySelectorAll() { return []; }});
  return fields.get(selector);
};
const context = vm.createContext({document: {querySelector: node}});
vm.runInContext(source, context);
node("#trade-asset-class").value = "TREASURY";
for (const operation of ["BUY", "SELL"]) {
  context.setOperationFields(operation);
  assert.equal(node("#quantity").step, "0.01");
  assert.equal(node("#quantity").min, "0.01");
  assert.equal(node("#quantity").required, true);
  assert.equal(node("#unit_price").required, true);
  assert.equal(node("#unit_price").step, "0.000001");
  assert.equal(node("#treasury-title").disabled, false);
  assert.equal(node("#treasury-title").parent.hidden, false);
  assert.equal(node("#trade-details").hidden, false);
  assert.equal(node("#asset-details").hidden, true);
  assert.equal(node("#ticker").required, false);
  assert.equal(node("#fixed-income-sale-details").hidden, true);
}
for (const kind of ["BRAZILIAN_STOCK", "BRAZILIAN_ETF", "FII"]) {
  node("#trade-asset-class").value=kind;
  context.setOperationFields("BUY");
  assert.equal(node("#quantity").step, "1");
  assert.equal(node("#asset-details").hidden, false);
  assert.equal(node("#ticker").required, true);
  assert.equal(node("#quantity").min, "1");
  assert.equal(node("#treasury-title").disabled, true);
}
node("#trade-asset-class").value="CRYPTO";
context.setOperationFields("BUY");
assert.equal(node("#quantity").step, "any");
assert.match(source, /amendTreasuryTrade\(dialog.dataset.treasuryEventId/);
assert.match(source, /expected_revision: Number\(dialog.dataset.treasuryRevision\)/);
assert.doesNotMatch(source, /<option>TESOURO_DIRETO<\/option>/);
console.log("Treasury operations: title units in buys/sales, B3 integer controls, crypto fractions and versioned amendment binding passed.");
