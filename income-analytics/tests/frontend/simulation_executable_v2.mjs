import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync("src/income_analytics/api/static/js/features/simulation-executable.js", "utf8");
const context = vm.createContext({assetClassLabel: value => value, Intl, BigInt});
vm.runInContext(source.replace(/^import .*;$/gm, "").replaceAll("export function", "function"), context);
const data = {
 base_currency: "BRL", status: "PARTIAL", budget: "50", total_estimated: "34.50", estimated_costs: "0", remaining_amount: "15.50", residual_amount: "5.50", unavailable_budget: "10", instruments: [],
 orders: [{ticker: "<img src=x>", label: "A & B", asset_class: "CRYPTO", market: "BR", quantity: "1E-8", quantity_step: "1E-8", unit_price: "34.5", currency: "BRL", price_date: "2026-10-24", price_source: "manual", price_age_days: 0, estimated_total: "34.50", costs_known: false, weight_before: null, weight_after: ".2", target_weight: ".3"}],
 blocked: [{ticker: "OTHER", reason: "STALE_PRICE", reserved_amount: "10"}],
};
const html = context.renderExecutablePlan(data, "<section>Comparison</section>");
assert.match(html, /0,00000001 unidades/);
assert.match(html, /&lt;img src=x&gt;/);
assert.doesNotMatch(html, /<img/);
assert.match(html, /A &amp; B/);
assert.match(html, /Saldo residual/);
assert.match(html, /Orçamento aguardando dados/);
assert.match(html, /fora da política de validade/);
assert.match(html, /não é cotação em tempo real/);
assert.match(html, /Custos da corretora não informados/);
assert.match(html, /Comparison/);
const blocked = context.renderExecutablePlan({...data, status: "INSUFFICIENT"});
assert.match(blocked, /Nenhuma compra foi sugerida/);
assert.doesNotMatch(blocked, /0,00000001 unidades/);
const input = (name, value, type="number", checked=false) => ({dataset:{rule:name}, value, type, checked});
const field = {dataset:{tradingRule:"ABC"},querySelectorAll:()=>[input("quantity_step",".001"),input("fractional_supported","", "checkbox", true),input("fee_percent",".25"),input("amount_increment", "")]};
const rules = context.collectTradingRules({querySelectorAll:()=>[field]});
assert.equal(rules.ABC.quantity_step, ".001");
assert.equal(rules.ABC.fractional_supported, true);
assert.equal(rules.ABC.fee_rate, "0.00250000");
assert.equal(rules.ABC.amount_increment, undefined);
console.log("Executable simulation: precise quantities, dated prices, residual/data separation, safe labels and broker rule serialization passed.");

const tiny = context.renderExecutablePlan({...data, orders:[{...data.orders[0], unit_price:"1E-18"}]});
assert.match(tiny, /1E-18 BRL/);
const events = {};
const step = {value:"1"}, minimum = {value:"1"};
const fractional = {checked:false,addEventListener:(event, fn)=>events.fractional=fn};
const precision = {value:"6",addEventListener:(event, fn)=>events.precision=fn};
const controls = {fractional_supported:fractional, quantity_precision:precision, quantity_step:step, minimum_quantity:minimum};
context.bindTradingRules({querySelectorAll:()=>[{querySelector:selector=>controls[selector.match(/data-rule="([^"]+)/)[1]]}]});
fractional.checked = true; events.fractional();
assert.equal(Number(step.value), .000001);
assert.equal(Number(minimum.value), .000001);
minimum.value = ".1"; precision.value = "8"; events.precision();
assert.equal(Number(step.value), .00000001);
assert.equal(minimum.value, ".1", "an explicit broker minimum stays intact");

const globalPlan = context.renderExecutablePlan({...data, unavailable_budget:"0", blocked:[{ticker:"MISSING",reason:"MISSING_PRICE",reserved_amount:"0"}], residual_reasons:["MINIMUM_EXCEEDS_BALANCE","GLOBAL_STRATEGY_LIMIT","MISSING_PRICE"]});
assert.match(globalPlan, /uma unidade ou lote mínimo supera/);
assert.match(globalPlan, /não melhoram a aderência global/);
assert.match(globalPlan, /cotação ou câmbio válidos/);
assert.doesNotMatch(globalPlan, /0,00 a aguardar dados/);
const limited = context.renderExecutablePlan({...data, residual_reasons:["SEARCH_LIMIT"]});
assert.match(limited, /não é considerado inevitável/);
