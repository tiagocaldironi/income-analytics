import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("src/income_analytics/api/static/js/features/portfolio.js", "utf8")
  .replace(/^import .*;\r?\n/gm, "")
  .replaceAll("export async function", "async function").replaceAll("export function", "function");
const positions = {innerHTML: "", closest: () => null};
const context = vm.createContext({document: {querySelector: selector => selector === "#positions" ? positions : null},
  money: (value, code) => `${code} ${value}`, percentage: value => `${value}%`,
  financialConcepts: {returnTooltip: "TWR"}, table: (headers, rows) => `<table><thead>${headers.join("|")}</thead>${rows.join("")}</table>`});
vm.runInContext(source, context);
const asset = (ticker, value, extra = {}) => ({asset_id: ticker, ticker, name: ticker, quantity: "0.05",
  average_price: 1000, current_price: 1100, market_value: value, total_result: 5,
  return_percentage: 10, income_received: 0, portfolio_weight: 0.5, target_weight: null, currency_code: "BRL", ...extra});
const select = group => Array.from(context.selectHoldingAssets(group), row => row.ticker);
for (const kind of ["FII", "BRAZILIAN_STOCK", "BRAZILIAN_ETF", "INTERNATIONAL", "CRYPTO", "TREASURY", "FIXED_INCOME"]) {
  const group = {asset_class: kind, assets: [asset("A", 20), asset("D", null), asset("B", 50), asset("C", "invalid"), asset("E", 50)]};
  assert.deepEqual(select(group), ["B", "E", "A", "C", "D"]);
  context.testGroup = group;
  vm.runInContext('holdingsQuery="B"', context);
  assert.deepEqual(select(group), ["B"]);
  vm.runInContext('holdingsQuery=""', context);
}
const mixed = {asset_class: "INTERNATIONAL", assets: [asset("USD", 100, {currency_code: "USD", market_value_base: 500}), asset("BRL", 300, {market_value_base: 300})]};
assert.deepEqual(select(mixed), ["USD", "BRL"]);
vm.runInContext('holdingsSort="name"', context);
assert.deepEqual(select(mixed), ["BRL", "USD"]);
vm.runInContext('holdingsSort="value-desc"', context);

const bankLots = {asset_class:"FIXED_INCOME", assets:[
  asset("A1",100,{contract_key:"A",name:"A",market_value_base:100}),
  asset("A2",100,{contract_key:"A",name:"A",market_value_base:100}),
  asset("B",150,{contract_key:"B",name:"B",market_value_base:150})]};
assert.deepEqual(select(bankLots),["A1","B"]);
assert.equal(context.selectHoldingAssets(bankLots)[0].market_value_base,200);

const treasury = asset("FI-INTERNAL", 55, {name: "LFT 2031", display_group: "TREASURY", display_name: "Tesouro Selic 2031", quantity_unit: "TITLE", treasury_trade_supported: true});
const row = context.renderHoldingRow(treasury, false, "TREASURY", "Tesouro Direto");
assert.match(row, /<strong>Tesouro Selic 2031<\/strong>/);
assert.doesNotMatch(row, /<strong>FI-INTERNAL<\/strong>/);
assert.match(row, /Identificador: FI-INTERNAL/);
assert.match(row, /data-label="Quantidade">0,05/);
assert.match(row, /data-operation-class="TREASURY"/);
const legacy = context.renderHoldingRow({...treasury, quantity_unit: "LEGACY_CONTRACT", treasury_trade_supported: false}, false, "TREASURY");
assert.match(legacy, /Contrato legado/);
assert.doesNotMatch(legacy, /data-open-operation/);
const groups = [{asset_class: "TREASURY", label: "Tesouro Direto", market_value: 55, total_cost: 50, weight: 0.5, target_weight: null, assets: [treasury]},
  {asset_class: "FIXED_INCOME", label: "Renda Fixa Bancária e outros", market_value: 55, total_cost: 50, weight: 0.5, target_weight: null, assets: [asset("CDB", 55)]}];
const snapshot = {classes: [{asset_class: "FIXED_INCOME", assets: [treasury]}], display_groups: groups};
const before = JSON.stringify(snapshot);
context.renderPortfolio({}, snapshot, null);
assert.match(positions.innerHTML, /Ativos de Tesouro Direto/);
assert.match(positions.innerHTML, /Título\|Quantidade\|Preço médio\|Preço atual/);
assert.match(positions.innerHTML, /Renda Fixa Bancária/);
assert.equal(JSON.stringify(snapshot), before);
console.log("Treasury: default sorting across all classes, search, explicit sort, FX comparison, names, legacy units and separate tables passed.");
