import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const root="src/income_analytics/api/static/";
const positions={innerHTML:"",closest:()=>({classList:{add(){}},querySelector:()=>({textContent:""})})};
const context=vm.createContext({document:{querySelector:s=>s==="#positions"?positions:s==="#open-allocation-policy"?{}:null},money:v=>String(v),percentage:v=>String(v)+"%",financialConcepts:{returnTooltip:"TWR"},table:(heads,rows)=>'<table><thead>'+heads.map(h=>'<th>'+h+'</th>').join('')+'</thead>'+rows.join('')+'</table>'});
const source=fs.readFileSync(root+'js/features/portfolio.js','utf8').replace(/^import .*;\r?\n/gm,'').replaceAll('export async function','async function').replaceAll('export function','function');
vm.runInContext(source,context);
const base={asset_class:'FIXED_INCOME',label:'Renda Fixa',assets:[{asset_id:'test',ticker:'TEST',name:'Teste',quantity:1,market_value:100,total_result:null,return_percentage:null,current_price:null,portfolio_weight:null,target_weight:null}],market_value:100,total_cost:80,weight:.4,target_weight:.2,deviation:.2,performance_coverage:null};
context.renderPortfolio({}, {base_currency:'BRL',classes:[base,{...base,asset_class:'FII',label:'FIIs',target_weight:null}]},null);
const html=positions.innerHTML;
assert.equal((html.match(/holding-class-statistics/g)||[]).length,2);
assert.equal((html.match(/holding-class-value/g)||[]).length,2);
assert.ok(html.includes('Peso ideal'));assert.ok(html.includes('Desvio 20%'));
assert.equal((html.match(/holding-class-action[^>]*><svg/g)||[]).length,2);
assert.ok(html.includes('data-group-distribution'));
assert.ok(!html.includes('◔'));
const distribution = context.groupDistributionData({
  asset_class: "INTERNATIONAL", label: "Exterior", market_value: null,
  assets: [
    {ticker: "OPEN", quantity: "2", currency_code: "USD", market_value: "40", market_value_base: "200"},
    {ticker: "GOAL", target_only: true, quantity: 1, market_value_base: "300"},
    {ticker: "SOLD", quantity: "0", market_value_base: "400"},
    {ticker: "MISSING", quantity: 1, market_value_base: null, market_value: 90, currency_code: "BRL"},
    {ticker: "INVALID", quantity: 1, market_value_base: "NaN"},
    {ticker: "LOCAL", quantity: 1, market_value: "50", currency_code: "BRL"},
  ],
}, "BRL");
assert.deepEqual(JSON.parse(JSON.stringify(distribution)), {
  assets: [
    {name: "OPEN", marketValue: 200, currency: "BRL"},
    {name: "LOCAL", marketValue: 50, currency: "BRL"},
  ],
  total: 250,
  partial: true,
});
const legend = context.renderGroupDistribution({label: "Exterior"}, distribution.assets,
  distribution.total, distribution.partial);
assert.ok(legend.includes("Total com valor disponível"));
assert.ok(legend.includes("80%") && legend.includes("20%"));
assert.ok(!/NaN|SOLD|GOAL|MISSING|INVALID/.test(legend));
const requests = [];
const apiContext = vm.createContext({
  AbortController, Headers, URLSearchParams, performance,
  window: {
    localStorage: {getItem: () => "portfolio-test"},
    setTimeout, clearTimeout,
  },
  fetch: async (path, options) => {
    requests.push([path, options.method || "GET", options.headers.get("X-Portfolio-Id")]);
    return {ok: true, json: async () => ({})};
  },
});
const apiSource = fs.readFileSync(root + "js/api.js", "utf8")
  .replace(/^import .*;\r?\n/gm, "")
  .replace("export const portfolioApi", "const portfolioApi");
await vm.runInContext(
  apiSource + "\nPromise.all([portfolioApi.contractHistory('lot-1'), "
  + "portfolioApi.contractPerformance('lot-1', '2026-01-01', '2026-11-25')]);",
  apiContext,
);
assert.deepEqual(requests, [
  ["/api/portfolio/history?period_months=12&contract_id=lot-1", "GET", "portfolio-test"],
  ["/api/portfolio/performance?contract_id=lot-1&start_date=2026-01-01&end_date=2026-11-25",
    "GET", "portfolio-test"],
]);
const index=fs.readFileSync(root+'index.html','utf8');
assert.ok(index.includes('holdings-heading'));
assert.ok(index.includes('holdings-actions'));
assert.ok(index.includes('id="portfolio-new-operation"'));
assert.ok(!index.includes('data-navigate>＋ Adicionar investimento</a>'));
assert.ok(source.includes('income:open-operation'));assert.ok(index.includes('id="open-allocation-policy"'));
console.log('Portfolio alignment: targets and metrics retained, SVG disclosure and allocation toolbar present.');
