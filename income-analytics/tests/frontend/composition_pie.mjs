import assert from 'node:assert/strict';
import fs from 'node:fs';import vm from 'node:vm';
const target={innerHTML:''};const ctx=vm.createContext({document:{querySelector:s=>s==='#class-allocation'?target:null},percentage:v=>`${v}%`,money:v=>String(v),emptyState:t=>t});
vm.runInContext(fs.readFileSync('src/income_analytics/api/static/js/features/portfolio.js','utf8').replace(/^import .*;\r?\n/gm,'').replaceAll('export async function','async function').replaceAll('export function','function'),ctx);
const data={base_currency:'BRL',portfolio_drift:null,classes:[{label:'A & B',asset_class:'FII',market_value:75},{label:'ETF',asset_class:'BRAZILIAN_ETF',market_value:25},{label:'Ausente',asset_class:'OTHER',market_value:null}]};
const before=JSON.stringify(data);ctx.renderClasses(data,[]);assert.match(target.innerHTML,/conic-gradient/);assert.match(target.innerHTML,/0% 75%/);assert.match(target.innerHTML,/75% 100%/);assert.match(target.innerHTML,/A &amp; B/);assert.match(target.innerHTML,/Valuation indisponível/);assert.ok(!target.innerHTML.includes('allocation-segmented-bar'));assert.equal(JSON.stringify(data),before);
ctx.renderClasses({...data,classes:[]},[]);assert.equal(target.innerHTML,'Composição indisponível');console.log('Composition pie: same proportions and values, safe labels, unavailable and empty states passed.');
