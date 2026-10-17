import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let source = fs.readFileSync("src/income_analytics/api/static/js/features/strategy.js", "utf8");
source = source.replace(/^import .*;\r?\n/gm, "").replaceAll("export async function", "async function").replaceAll("export function", "function");
const context = vm.createContext({ console, money: value => `R$ ${Number(value).toLocaleString("pt-BR")}`, friendlyError: error => String(error), assetClassLabel: value => value, document: { querySelector: () => null } });
vm.runInContext(source, context);
const classes = [
  { asset_class: "BRAZILIAN_STOCK", label: "Ações Brasil", current_weight: ".333398", target_weight: ".6", deviation: "-.266602", market_value: "30240.15", assets: [{ ticker: "PETR4", target_weight: null }], color: "#27c7a8" },
  { asset_class: "FII", label: "FIIs", current_weight: ".275185", target_weight: ".4", deviation: "-.124815", market_value: "24952.10", assets: [], color: "#5b9cff" },
  { asset_class: "FIXED_INCOME", label: "Renda fixa", current_weight: ".236878", target_weight: "0", deviation: ".236878", market_value: "21487.00", assets: [], color: "#8a6ce8" },
  { asset_class: "CRYPTO", label: "Cripto", current_weight: ".093710", target_weight: "0", deviation: ".093710", market_value: "8500", assets: [], color: "#e7b65a" },
];
const target = { innerHTML: "", querySelectorAll: () => [] };
context.render(target, { analysis: { portfolio_drift: ".391416" }, classes, valuationComplete: true });
assert.match(target.innerHTML, /Carteira atual × Carteira-alvo/);
assert.match(target.innerHTML, /39,1%/);
assert.match(target.innerHTML, /Ações Brasil/);
assert.match(target.innerHTML, /-26,7 p\.p\./);
assert.match(target.innerHTML, /Renda fixa/);
assert.match(target.innerHTML, /\+23,7 p\.p\./);
assert.match(target.innerHTML, /Sua política não contempla algumas classes/);
assert.match(target.innerHTML, /Sua carteira se desviou da estratégia ou sua estratégia mudou/);
assert.match(target.innerHTML, /Composição dentro das classes/);
assert.match(target.innerHTML, /Quer controlar também como cada classe é distribuída/);
assert.match(target.innerHTML, /Exterior/);
assert.match(target.innerHTML, /IVV/);
assert.match(target.innerHTML, /100% da classe/);
assert.match(target.innerHTML, /Definir composição por ativo/);
assert.match(target.innerHTML, /data-choose-asset-class/);
assert.match(target.innerHTML, /Onde estão as diferenças\?/);
assert.match(target.innerHTML, /Maior diferença: Ações Brasil · 26,7% abaixo do objetivo/);
assert.match(target.innerHTML, /data-strategy-differences/);
assert.match(target.innerHTML, /strategy-bullet/);
assert.match(target.innerHTML, /left:60%/);
assert(!target.innerHTML.includes("strategy-comparison-line"));
assert.match(source, /let strategyDifferencesOpen = false/);
assert(!target.innerHTML.includes(">BRAZILIAN_STOCK<"));
assert(!target.innerHTML.includes("Classe:percentual"));
assert.match(source, /save\.disabled = !valid/);
assert.match(source, /Math\.abs\(remaining\) < \.000001/);
assert.match(source, /portfolioApi\.assetAllocationPolicy/);
assert.match(source, /Qual classe você quer distribuir/);
const sessionSource = fs.readFileSync("src/income_analytics/application/portfolio_session.py", "utf8");
assert.match(sessionSource, /active_assets = tuple\(/);
assert.match(sessionSource, /if not position\.is_empty/);
assert.match(sessionSource, /target_tickers = \{ticker for targets in policy\.targets\.values\(\) for ticker in targets\}/);
assert.match(sessionSource, /policy\.validate_assets\(/);
const configuredComposition = context.assetTargets([
  { asset_class: "BRAZILIAN_STOCK", label: "Ações Brasil", target_weight: .6, composition_distance: .18, assets: [{ ticker: "PETR4", current_weight_in_class: .4, target_weight: .25, gap_pp: -.15 }, { ticker: "BBAS3", current_weight_in_class: .2, target_weight: .25, gap_pp: .05 }, { ticker: "ITSA4", current_weight_in_class: .2, target_weight: .2, gap_pp: 0 }, { ticker: "Outros", current_weight_in_class: .2, target_weight: .3, gap_pp: .1 }] },
  { asset_class: "FII", label: "FIIs", target_weight: .4, assets: [{ ticker: "KNRI11", target_weight: null }] },
]);
assert.match(configuredComposition, /Ações Brasil/);
assert.match(configuredComposition, /60,0% do patrimônio/);
assert.match(configuredComposition, /PETR4/);
assert.match(configuredComposition, /Como suas classes estão distribuídas por dentro/);
assert.match(configuredComposition, /Distância da composição/);
assert.match(configuredComposition, /Maiores diferenças/);
assert.match(configuredComposition, /Ver composição/);
assert.match(configuredComposition, /data-view-composition/);
assert.match(configuredComposition, /Editar/);
assert.match(configuredComposition, /Você acompanha apenas o objetivo total da classe/);
assert.match(configuredComposition, /Definir composição/);
assert.match(source, /composition-detail-dialog/);
assert.match(source, /Maior diferença/);
const partialTarget = { innerHTML: "", querySelectorAll: () => [] };
context.render(partialTarget, { analysis: { portfolio_drift: ".391416" }, classes, valuationComplete: false });
assert.match(partialTarget.innerHTML, /Parte da carteira não pôde ser avaliada/);
const invalidTarget = { innerHTML: "", querySelectorAll: () => [] };
context.render(invalidTarget, { analysis: { portfolio_drift: ".391416" }, classes: classes.map(item => ({ ...item, target_weight: .1 })), valuationComplete: true });
assert.match(invalidTarget.innerHTML, /A distribuição-alvo soma 40,0%/);
assert.match(invalidTarget.innerHTML, /Revise a estratégia para completar 100%/);
console.log("Strategy UX V2 frontend checks passed.");
