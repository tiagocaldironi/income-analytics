import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
// Regression: asset names and descriptions must be text, not markup.
const source=fs.readFileSync('src/income_analytics/api/static/js/features/portfolio.js','utf8').replace(/^import .*;\r?\n/gm,'').replaceAll('export async function','async function').replaceAll('export function','function');
const context=vm.createContext({money:()=> '0',percentage:()=> '0%'});
vm.runInContext(source,context);
const name='<em data-audit>Untrusted</em>';
const row=context.renderHoldingRow({name,asset_id:'test-only',ticker:'AUDIT',quantity:'1',average_price:1,current_price:1,market_value:1,total_result:1,return_percentage:1,income_received:0,portfolio_weight:1,target_weight:1,currency_code:'BRL'},true,'FIXED_INCOME');
assert.doesNotMatch(row,/<em data-audit>/);
assert.match(row,/&lt;em data-audit&gt;Untrusted&lt;\/em&gt;/);
console.log('XSS regression passed: holding name is escaped text.');
