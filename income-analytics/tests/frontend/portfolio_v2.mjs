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

// The sidebar preference survives setup and storage denial does not break navigation.
const sidebarSource=fs.readFileSync(base+'js/features/portfolio-view-v2.js','utf8').replace(/^import .*;$/gm,'').replaceAll('export function','function');
function sidebarHarness(stored='0', blocked=false){
 const classes=new Set();const attrs={};let click;let chartResizes=0;
 const toggle={id:'sidebar-toggle',setAttribute(k,v){attrs[k]=v;},addEventListener(type,fn){if(type==='click')click=fn;}};
 const storage={getItem(){if(blocked)throw Error('denied');return stored;},setItem(k,v){if(blocked)throw Error('denied');stored=v;}};
 const root={classList:{toggle(k,on){on?classes.add(k):classes.delete(k);},contains:k=>classes.has(k)}};
 const ctx=vm.createContext({document:{querySelector:()=>toggle,documentElement:root},localStorage:storage,requestAnimationFrame:fn=>{chartResizes++;fn();}});
 vm.runInContext(sidebarSource,ctx);ctx.setupSidebar();
 return {attrs,classes,toggle,click:()=>click(),stored:()=>stored,resizes:()=>chartResizes};
}
const sidebar=sidebarHarness('1');
assert.equal(sidebar.attrs['aria-expanded'],'false');
assert.equal(sidebar.attrs['aria-label'],'Expandir menu lateral');
sidebar.click();assert.equal(sidebar.attrs['aria-expanded'],'true');assert.equal(sidebar.stored(),'0');
sidebar.click();assert.ok(sidebar.classes.has('sidebar-collapsed'));assert.equal(sidebar.stored(),'1');
assert.equal(sidebar.resizes(),3);
const deniedSidebar=sidebarHarness('1',true);deniedSidebar.click();assert.equal(deniedSidebar.attrs['aria-expanded'],'false');
console.log('Sidebar: collapse/expand, accessible labels, persistence, resize and unavailable storage passed.');
