import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/intelligence.js", "utf8");
source = source.replace(/^import .*;\r?\n/gm, "").replaceAll("export function", "function").replace("export async function", "async function");
const context = vm.createContext({
  console,
  date: value => value ? `data ${value}` : "—",
  emptyState: message => `<div class="empty">${message}</div>`,
  document: { querySelector: () => null },
});
vm.runInContext(source, context);

const drift = {
  logical_key: "PORTFOLIO_DRIFT:PORTFOLIO:ALLOCATION_POLICY", code: "PORTFOLIO_DRIFT", category: "STRATEGY",
  current_value: "0.3914165460536653773858624262", materiality: "HIGH", trajectory: "UNKNOWN", should_surface: true,
  reference: { type: "INCOME_TECHNICAL_THRESHOLD", value: "0.10", policy: { type: "USER_ALLOCATION_POLICY" } },
  data_quality: { current_valuation_complete: true, comparison_valuation_complete: false },
  decomposition: [
    { label: "FIIs", current_weight: ".275", target_weight: ".4", deviation_pp: "-12.5" },
    { label: "Ações Brasil", current_weight: ".333", target_weight: ".6", deviation_pp: "-26.7" },
    { label: "Renda fixa", current_weight: ".237", target_weight: "0", deviation_pp: "23.7" },
    { label: "Cripto", current_weight: ".094", target_weight: "0", deviation_pp: "9.4" },
    { label: "Exterior", current_weight: ".056", target_weight: "0", deviation_pp: "5.6" },
  ],
};
const country = {
  logical_key: "COUNTRY_CONCENTRATION:COUNTRY:BR", code: "COUNTRY_CONCENTRATION", category: "EXPOSURE",
  subject: { label: "Brasil" }, current_value: ".843100655", materiality: "MEDIUM", trajectory: "UNKNOWN", should_surface: true,
  reference: { type: "INCOME_TECHNICAL_THRESHOLD", value: ".70" }, data_quality: { current_valuation_complete: true, comparison_valuation_complete: false }, decomposition: [],
};
const risk = {
  logical_key: "INCOMPLETE_RISK_COVERAGE:PORTFOLIO:RISK_COVERAGE", code: "INCOMPLETE_RISK_COVERAGE", category: "DATA_QUALITY",
  current_value: ".763121345", materiality: "MEDIUM", trajectory: "UNKNOWN", should_surface: true,
  reference: { type: "ANALYSIS_COMPLETENESS", value: "1" }, data_quality: { current_valuation_complete: true, comparison_valuation_complete: false }, decomposition: [],
};
const target = { innerHTML: "", querySelectorAll: () => [] };
context.renderAttention(target, { findings: [drift, country, risk, { ...country, logical_key: "hidden", should_surface: false }] });
assert.match(target.innerHTML, /2 pontos merecem atenção\. 1 limitação afeta a análise\./);
assert.match(target.innerHTML, /39,1%/);
assert(target.innerHTML.indexOf("Ações Brasil") < target.innerHTML.indexOf("Renda fixa"));
assert.match(source, /Alvo significa a política cadastrada por você/);
assert.match(target.innerHTML, /Brasil/);
assert.match(target.innerHTML, /84,3%/);
assert.match(target.innerHTML, /70,0%/);
assert.match(target.innerHTML, /\+14,3 p\.p\. acima da referência/);
assert.match(target.innerHTML, /Limitações da análise/);
assert.match(target.innerHTML, /76,3%/);
assert.match(target.innerHTML, /Isso não equivale a risco mensurado/);
assert.match(target.innerHTML, /Histórico insuficiente para avaliar tendência/);
assert(!target.innerHTML.includes("0.391416546"));
assert(!target.innerHTML.includes("DATA_QUALITY"));
assert(!target.innerHTML.includes("hidden"));

for (const [code, label] of Object.entries({ NEW: "Novo", WORSENING: "Piorando", IMPROVING: "Melhorando", PERSISTENT: "Persistente", UNKNOWN: "Histórico insuficiente" })) {
  assert.match(context.trajectoryText({ trajectory: code }), new RegExp(label));
}
const empty = { innerHTML: "", querySelectorAll: () => [] };
context.renderAttention(empty, { findings: [{ ...country, should_surface: false }] });
assert.match(empty.innerHTML, /Nenhum ponto relevante identificado/);
assert(!empty.innerHTML.includes("Sem riscos"));
console.log("Points of Attention UX V2 frontend checks passed.");
