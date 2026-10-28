import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const source=fs.readFileSync('src/income_analytics/api/static/js/features/portfolio.js','utf8').replace(/^import .*;\r?\n/gm,'').replaceAll('export async function','async function').replaceAll('export function','function');
const positions={innerHTML:'',closest:()=>null};
const ctx=vm.createContext({document:{querySelector:s=>s==='#positions'?positions:null},money:(v,c)=>`${c} ${v}`,percentage:v=>`${v}%`,financialConcepts:{returnTooltip:'TWR'},table:(h,rows)=>`<table>${rows.join('')}</table>`});vm.runInContext(source,ctx);
const asset=(name,market_value=100)=>({asset_id:name,ticker:name,name,quantity:1,average_price:90,current_price:market_value,market_value,total_result:market_value===null?null:market_value-90,return_percentage:null,income_received:3,portfolio_weight:.5,target_weight:null,currency_code:'BRL'});
const group={asset_class:'FII',label:'FIIs',market_value:200,total_cost:180,weight:1,target_weight:null,assets:[asset('Árvore'),asset('Beta',200),asset('Sem preço',null),{...asset('Apenas meta'),target_only:true}]};ctx.group=group;
vm.runInContext('holdingsQuery="arvore"',ctx);assert.equal(ctx.selectHoldingAssets(group)[0].name,'Árvore');
vm.runInContext('holdingsQuery="";holdingsSort="value-desc"',ctx);assert.deepEqual(Array.from(ctx.selectHoldingAssets(group),a=>a.name),['Beta','Árvore','Sem preço']);
vm.runInContext('holdingsSort="value-asc"',ctx);assert.equal(ctx.selectHoldingAssets(group).at(-1).name,'Sem preço');
ctx.renderPortfolio({}, {base_currency:'BRL',classes:[group]},null);assert.match(positions.innerHTML,/Total da classe/);assert.match(positions.innerHTML,/Preço não disponível/);assert.match(positions.innerHTML,/<b class="metric-pill positive">\+BRL 10<\/b>/);assert.match(positions.innerHTML,/data-holding-details/);assert.ok(!positions.innerHTML.includes('Apenas meta'));
vm.runInContext('holdingsQuery="inexistente";renderHoldings()',ctx);assert.match(positions.innerHTML,/Nenhum investimento encontrado nesta categoria/);
vm.runInContext('holdingsQuery="";holdingsClass="CRYPTO";renderHoldings()',ctx);assert.match(positions.innerHTML,/Limpar filtros/);
ctx.renderPortfolio({}, {classes:[]},null);assert.match(positions.innerHTML,/Seus investimentos aparecerão aqui/);
const unsafe=ctx.renderHoldingRow({...asset('<script>alert(1)</script>',80),asset_id:'" onclick="x'},false,'FII','FIIs');assert.ok(!unsafe.includes('<script>'));assert.match(unsafe,/&lt;script&gt;/);assert.match(unsafe,/<b class="metric-pill negative">BRL -10<\/b>/);assert.ok(!unsafe.includes('data-asset-id="" onclick='));
// Assert the result cell independently of other numeric columns.
const resultCell = (value) => {
  const row = ctx.renderHoldingRow({...asset('Resultado'), total_result:value}, false, 'FII', 'FIIs');
  return row.match(/<td data-label="Resultado">(.*?)<\/td>/)[1];
};
assert.equal(resultCell(10), '<b class="metric-pill positive">+BRL 10</b>');
assert.equal(resultCell(-10), '<b class="metric-pill negative">BRL -10</b>');
assert.equal(resultCell(0), '<b class="metric-pill ">Sem variação BRL 0</b>');
assert.equal(resultCell(null), '<b class="metric-pill ">Resultado indisponível</b>');
for (const value of [10, -10, 0, null]) assert.doesNotMatch(resultCell(value), /Ganho|Perda/);
const before=JSON.stringify(group);vm.runInContext('holdingsQuery="";holdingsSort="name"',ctx);ctx.selectHoldingAssets(group);assert.equal(JSON.stringify(group),before);
console.log('Holdings V2: accent-insensitive search, sorting/nulls, filters, empty/target-only, XSS, signs, details and immutable values passed.');
