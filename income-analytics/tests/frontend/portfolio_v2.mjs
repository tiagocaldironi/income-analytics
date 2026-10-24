import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const base="src/income_analytics/api/static/";
const css=fs.readFileSync(base+"css/design-system-v2.css","utf8");
function luminance(hex){const a=hex.replace("#","").match(/../g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return .2126*a[0]+.7152*a[1]+.0722*a[2];}
function contrast(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
for(const section of [css.match(/:root\{([^}]+)/)[1],css.match(/html\[data-theme="light"\]\{([^}]+)/)[1]]){
 const tokens=Object.fromEntries([...section.matchAll(/--income-([a-z-]+):(#(?:[0-9a-f]{6}|[0-9a-f]{3}))(?=;|$)/g)].map(m=>[m[1],m[2].length===4?'#'+[...m[2].slice(1)].map(x=>x+x).join(''):m[2]]));
 for(const text of ['text','secondary','positive','negative']) assert.ok(contrast(tokens[text],tokens.surface)>=4.5,text);
 assert.ok(contrast(tokens.action,tokens.context)>=4.5,'action/context');
 assert.ok(contrast(tokens.focus,tokens.bg)>=3,'focus');
}
assert.ok(contrast('#ffffff','#245bd6')>=4.5);
let resized=0, focus=-1;
const tabs=Array.from({length:4},(_,i)=>({dataset:{analysisTab:String(i)},attributes:{},setAttribute(k,v){this.attributes[k]=v;},focus(){focus=i;}}));
const panels=tabs.map(()=>({hidden:false,filter:{value:'12'}}));
const events={}; const touch={};
const region={addEventListener:(type,fn)=>events[type]=fn,querySelector:s=>s==='[role=tablist]'?{addEventListener:(type,fn)=>touch[type]=fn}:tabs.find(t=>t.attributes['aria-selected']==='true')};
const context=vm.createContext({document:{querySelector:()=>region,querySelectorAll:s=>s==='[data-analysis-tab]'?tabs:s==='[data-analysis-panel]'?panels:[],documentElement:{}},requestAnimationFrame:fn=>fn(),MutationObserver:class{observe(){}},renderPortfolioGuidance(){}});
vm.runInContext(fs.readFileSync(base+'js/features/portfolio-view-v2.js','utf8').replace(/^import .*;$/gm,'').replaceAll('export function','function'),context);
context.setupPortfolioView(()=>resized++);
context.selectAnalysis(2,true);assert.equal(focus,2);assert.deepEqual(panels.map(p=>p.hidden),[true,true,false,true]);
assert.equal(panels[0].filter.value,'12');
events.keydown({target:{closest:()=>tabs[2]},key:'End',preventDefault(){}});assert.equal(focus,3);
events.keydown({target:{closest:()=>tabs[3]},key:'ArrowRight',preventDefault(){}});assert.equal(focus,0);
touch.touchstart({changedTouches:[{clientX:200,clientY:10}]});touch.touchend({changedTouches:[{clientX:40,clientY:12}]});assert.equal(tabs[1].attributes['aria-selected'],'true');
assert.equal(resized,4);
const emptyContext=vm.createContext({});
vm.runInContext(fs.readFileSync(base+'js/features/portfolio-guidance-v2.js','utf8').replace(/^import .*;$/gm,'').replaceAll('export async function','async function').replaceAll('export function','function'),emptyContext);
const empty={holdings:{classes:[]},history:{snapshots:[]},portfolio:{}};
assert.equal(emptyContext.portfolioIsEmpty(empty),true);
assert.equal(emptyContext.portfolioIsEmpty({...empty,history:{snapshots:[{}],history_boundary:{source:'NO_OBSERVED_FINANCIAL_EVENTS'}}}),true,'zero baseline is not a registered investment');
assert.equal(emptyContext.portfolioIsEmpty({...empty,history:{snapshots:[{}]}}),false,'closed positions still have history');
assert.equal(emptyContext.portfolioIsEmpty({...empty,holdings:{classes:[{assets:[{target_only:true}]}]}}),true);
assert.equal(emptyContext.portfolioIsEmpty({...empty,portfolio:{cash:100}}),false);
console.log('Portfolio V2: AA tokens, persistent panels, keyboard/swipe and real empty-state classification passed.');
