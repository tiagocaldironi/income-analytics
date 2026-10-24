import assert from 'node:assert/strict';import fs from 'node:fs';import vm from 'node:vm';
let wallet='a';const pending=[];const writes=[];const events={};const windowEvents={};
const target={hidden:false,innerHTML:'',replaceChildren(){this.innerHTML='';}};
const page={dataset:{},querySelector:()=>({after(){}})};
const state=id=>({portfolio_id:id,portfolio_name:`Wallet ${id}`,status:'ACTIVE',last_step:2,ask_intent:false,intent:'EXISTING',classes:[],facts:{available_analyses:[]},achievements:[]});
const ctx=vm.createContext({localStorage:{getItem:()=>wallet},icon:()=>'<svg></svg>',document:{querySelector:s=>s==='#portfolio-guidance'?target:s==='[data-page="minha-carteira"]'?page:null,querySelectorAll:()=>[],addEventListener:(t,f)=>events[t]=f},window:{addEventListener:(t,f)=>windowEvents[t]=f,dispatchEvent(){}},CustomEvent:class{constructor(type,options){this.type=type;this.detail=options?.detail;}},portfolioApi:{contextualOnboarding:id=>new Promise(resolve=>pending.push({id,resolve})),saveContextualOnboarding:async(id,body)=>{writes.push({id,body});return state(id);}}});
vm.runInContext(fs.readFileSync('src/income_analytics/api/static/js/features/portfolio-guidance-v2.js','utf8').replace(/^import .*;$/gm,'').replaceAll('export async function','async function').replaceAll('export function','function'),ctx);
const data={holdings:{classes:[]},portfolio:{},history:{snapshots:[]}};
const old=ctx.renderPortfolioGuidance(data);wallet='b';ctx.invalidatePortfolioGuidance();const fresh=ctx.renderPortfolioGuidance(data);
pending[1].resolve(state('b'));await fresh;pending[0].resolve(state('a'));await old;
assert.ok(target.innerHTML.includes('Wallet b'));assert.ok(!target.innerHTML.includes('Wallet a'));
assert.equal(writes.filter(w=>w.id==='a').length,0,'late old wallet cannot start progress');
await ctx.save({action:'SKIP'});assert.equal(writes.at(-1).id,'b');
wallet='c';await ctx.save({action:'DISMISS'});assert.equal(writes.at(-1).id,'b','wallet mismatch prevents write');
assert.ok(fs.readFileSync('src/income_analytics/api/static/js/features/operations.js','utf8').includes('income:operation-confirmed'));
console.log('Onboarding V2: late response isolation, safe wallet writes, persisted state rendering and operation confirmation integration passed.');

wallet='b';ctx.portfolioApi.saveContextualOnboarding=async()=>{throw Error('offline');};
assert.equal(await ctx.save({action:'EXPLORE',analysis:'composition'}),false);
assert.ok(target.innerHTML.includes('Wallet b'),'failed save keeps confirmed prior progress');
console.log('Onboarding V2: failed persistence cannot report completion.');

const progress=ctx.renderOnboardingAchievements([{id:'wallet_created',title:'A < B',description:'Real wallet',state:'COMPLETED'},{id:'first_investment',title:'First',description:'Confirmed save',state:'IN_PROGRESS'}]);
assert.match(progress,/A &lt; B/);assert.match(progress,/Real wallet/);assert.match(progress,/Concluído/);assert.match(progress,/Em andamento/);
