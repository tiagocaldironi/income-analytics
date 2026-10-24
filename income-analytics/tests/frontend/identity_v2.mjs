import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const base='src/income_analytics/api/static/';
const ctx=vm.createContext({});vm.runInContext(fs.readFileSync(base+'js/shared/icons.js','utf8').replace('export function','function'),ctx);
const shapes=['moneybag','tools','settings','help'].map(name=>ctx.icon(name));assert.equal(new Set(shapes).size,4);
for(const shape of shapes){assert.match(shape,/<svg/);assert.match(shape,/aria-hidden="true"/);assert.match(shape,/stroke="currentColor"/);assert.ok(!shape.includes('undefined'));}
const logo=fs.readFileSync(base+'img/income-mark.svg','utf8');assert.equal((logo.match(/<path/g)||[]).length,1);assert.ok(!logo.includes('#B8D5FF'));
const css=fs.readFileSync(base+'css/app.css','utf8');assert.ok(!css.includes('linear-gradient(135deg, #22bda6, #149d98)'));assert.ok(css.includes('var(--income-action-bg, #245bd6)'));
const view=fs.readFileSync(base+'js/features/portfolio-view-v2.js','utf8');assert.ok(view.includes('"moneybag"'));assert.ok(view.includes('"#ferramentas":"tools"'));assert.ok(view.includes('"#ajuda-metodologia":"help"'));
console.log('Identity V2: distinct semantic SVG icons, bars-only logo and token-based legacy primary actions passed.');
