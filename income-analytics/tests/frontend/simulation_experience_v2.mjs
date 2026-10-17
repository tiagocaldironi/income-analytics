import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/simulation.js", "utf8");
source = source.replace(/^import .*;\r?\n/gm, "").replaceAll("export async function", "async function").replaceAll("export function", "function");
const context = vm.createContext({
  console,
  money: value => `R$ ${Number(value).toFixed(2)}`,
  friendlyError: error => String(error?.message || error),
  assetClassLabel: value => ({ US_REIT: "REITs EUA", INTERNATIONAL: "Exterior", BRAZILIAN_STOCK: "Ações Brasil" })[value] || value,
  portfolioApi: {},
});
vm.runInContext(source, context);

const result = {
  status: "COMPLETE",
  issues: [],
  scenario: {
    contribution_amount: "5000",
    unallocated_amount: "0",
    class_allocations: [
      {
        asset_class: "US_REIT",
        amount: "1041.51",
        asset_distribution_status: "DISTRIBUTED_BY_STRATEGY",
        asset_distributed_amount: "1041.51",
        undistributed_within_class: "0",
        asset_allocations: [
          { asset_label: "AMT", amount: "374.86", weight_before_in_class: ".2596", weight_after_in_class: ".33", target_weight_in_class: ".33" },
          { asset_label: "DLR", amount: "335.86", weight_before_in_class: ".3813", weight_after_in_class: ".34", target_weight_in_class: ".34" },
          { asset_label: "PLD", amount: "330.79", weight_before_in_class: ".3592", weight_after_in_class: ".33", target_weight_in_class: ".33" },
        ],
      },
      { asset_class: "INTERNATIONAL", amount: "2225.70", asset_distribution_status: "NEEDS_USER_DISTRIBUTION", asset_distributed_amount: "0", undistributed_within_class: "2225.70", asset_allocations: [] },
    ],
  },
  comparison: {
    wealth_before: "90706.87",
    invested_wealth_after: "95706.87",
    strategy_distance_before: ".2023",
    strategy_distance_after: ".1656",
    strategy_distance_change: "-.0367",
    class_changes: [
      { asset_class: "US_REIT", weight_before: ".0049", weight_after: ".0155", target_weight: ".05", weight_change_pp: ".0106" },
      { asset_class: "BRAZILIAN_STOCK", weight_before: ".3334", weight_after: ".316", target_weight: ".25", weight_change_pp: "-.0174" },
    ],
  },
};

const html = context.renderResult(result);
assert.match(html, /Seu cenário/);
assert.match(html, /Patrimônio investido/);
assert.match(html, /20,23%/);
assert.match(html, /16,56%/);
assert.match(html, /mais próximo da estratégia cadastrada/);
assert.match(html, /Hoje → Cenário → Objetivo/);
assert.match(html, /Ações Brasil/);
assert.match(html, /Como o aporte seria distribuído/);
assert.match(html, /REITs EUA/);
assert.match(html, /AMT/);
assert.match(html, /25,96% → <strong>33,0%<\/strong> → 33,0%/);
assert.match(html, /Sua estratégia define o objetivo da classe/);
assert.match(html, /A definir dentro da classe/);
assert.match(html, /Ver detalhes do cenário/);
assert(!html.includes("US_REIT"));

const residual = structuredClone(result);
residual.scenario.unallocated_amount = "100";
assert.match(context.renderResult(residual), /Não distribuído/);

const invalid = structuredClone(result);
invalid.scenario.class_allocations[0].asset_distribution_status = "INCOMPLETE_OR_INVALID_POLICY";
assert.match(context.renderResult(invalid), /composição-alvo da classe está incompleta/);

assert.match(context.renderResult({ status: "INSUFFICIENT", issues: ["MISSING_FX"] }), /converter uma ou mais posições/);
assert.match(source, /mode: "STRATEGY_GUIDED"/);
assert.match(source, /include_asset_distribution: true/);
assert.match(source, /Informe um valor maior que zero/);
assert.doesNotMatch(source, /target_weight.*\/.*wealth|strategy_distance.*[-+]/);
console.log("Simulation Experience V2 frontend checks passed.");
