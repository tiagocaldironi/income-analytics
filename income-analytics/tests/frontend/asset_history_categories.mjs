import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("src/income_analytics/api/static/js/features/portfolio.js", "utf8");
const functions = source.slice(source.indexOf("async function loadAssetTransactions("), source.indexOf("\nfunction formatDate("));
const requests = [];
const data = { items: [{ id: "event", operation: "Dividendo", effective_date: "2026-10-24", amount: 12.34, currency_code: "BRL", source: "fixture", quantity: null, unit_price: null }], page: 2, total_pages: 3, movement_count: 4, income_count: 3, has_previous: true, has_next: true };
const ctx = vm.createContext({
  portfolioApi: { async assetTransactions(id, params) { requests.push({id, params}); return data; } },
  loadingState: "Carregando", errorState: value => value,
  emptyState: value => `<p>${value}</p>`, escapeHtml: value => String(value),
  formatDate: value => value, money: value => String(value),
  table: (headers, rows) => `<table>${rows.join("")}</table>`,
});
vm.runInContext("let assetTransactionsRequestId=0;\n" + functions, ctx);
const income = ctx.renderAssetTransactions(data, "INCOME");
assert.ok(income.includes('data-events-pane="income"'));
assert.ok(!/data-events-pane="income"[^>]*hidden/.test(income));
assert.ok(income.includes("Dividendo") && income.includes("12.34"));
assert.ok(income.includes('data-asset-transactions-page="3"'));
assert.ok(!income.includes('data-events-pane="movement"'));
const movement = ctx.renderAssetTransactions(data, "MOVEMENT");
assert.ok(movement.includes('data-events-pane="movement"'));
assert.ok(!movement.includes('data-events-pane="income"'));
assert.ok(ctx.renderAssetTransactions({...data,items:[]}, "INCOME").includes("Nenhum rendimento"));
const content = {innerHTML:"",setAttribute(){}};
const dialog = {dataset:{assetId:"asset",eventsGroup:"INCOME"},open:true,_eventViews:{income:{page:1},movement:{page:1}},querySelector(){return content;},querySelectorAll(){return [];}};
await ctx.loadAssetTransactions(dialog, 2);
assert.equal(requests.at(-1).params.group, "INCOME");
assert.equal(dialog._eventViews.income.page, 2);
assert.ok(content.innerHTML.includes("Dividendo"));
await ctx.loadAssetTransactions(dialog, 1, "MOVEMENT");
assert.equal(requests.at(-1).params.group, "MOVEMENT");
assert.equal(dialog.dataset.eventsGroup, "MOVEMENT");
ctx.portfolioApi.assetTransactions = async (id,params) => {
  requests.push({id,params});
  return {...data,total_pages:1,page:params.page};
};
await ctx.loadAssetTransactions(dialog, 2, "INCOME");
assert.equal(requests.at(-1).params.page,1);
assert.equal(dialog._eventViews.income.page,1);
console.log("Asset history categories: visible income, correct panes, pagination, refresh context and last-page fallback passed.");


// Confirm/cancel/retry operate inside the modal, without native browser dialogs.
const deleteFunctions = source.slice(source.indexOf("function showAssetDeletion("), source.indexOf("async function loadAssetTransactions("));
const elements = new Map();
const element = () => ({hidden:true,disabled:false,textContent:"",focusCount:0,focus(){this.focusCount++;}});
const get = selector => {if(!elements.has(selector)) elements.set(selector,element()); return elements.get(selector);};
let deletionCount = 0, fail = true, finish;
const refreshes = [];
const deletionContext = vm.createContext({
  portfolioApi: {deleteOperation: async id => {assert.equal(id,"event");deletionCount++;if(fail)throw new Error("Falha de teste");await new Promise(resolve=>{finish=resolve;});}},
  formatDate:value=>value,money:value=>String(value),
  loadAssetTransactions:async (dialog,page,group)=>refreshes.push({page,group}),
  loadPortfolio:async (asOf,options)=>refreshes.push(options),
});
vm.runInContext(deleteFunctions,deletionContext);
const trigger={dataset:{deleteAssetTransaction:"event"},isConnected:true,focusCount:0,focus(){this.focusCount++;}};
const confirmDialog={dataset:{assetId:"asset",eventsGroup:"INCOME"},open:true,_eventItems:data.items,_eventViews:{income:{page:2}},querySelector:get,querySelectorAll:()=>[get("tab"),get("close")]};
deletionContext.showAssetDeletion(confirmDialog,trigger);
assert.equal(deletionCount,0);
assert.equal(get("[data-delete-confirmation]").hidden,false);
assert.equal(get("[data-cancel-asset-delete]").focusCount,1);
deletionContext.dismissAssetDeletion(confirmDialog);
assert.equal(trigger.focusCount,1);
assert.equal(confirmDialog._pendingDeletion,null);
deletionContext.showAssetDeletion(confirmDialog,trigger);
await deletionContext.deleteAssetTransaction(confirmDialog);
assert.equal(get("[data-delete-error]").hidden,false);
assert.equal(get("[data-delete-error]").textContent,"Falha de teste");
assert.equal(refreshes.length,0);
assert.equal(get("[data-confirm-asset-delete]").disabled,false);
fail=false;
const pendingDelete=deletionContext.deleteAssetTransaction(confirmDialog);
await deletionContext.deleteAssetTransaction(confirmDialog);
assert.equal(deletionCount,2); // One failed attempt, then one pending request; no duplicate.
assert.equal(get("[data-confirm-asset-delete]").disabled,true);
finish();await pendingDelete;
assert.equal(refreshes[0].group,"INCOME");
assert.equal(refreshes[0].page,2);
assert.equal(refreshes[1].preserveTransactions,true);
assert.equal(confirmDialog._pendingDeletion,null);
assert.equal(get("[data-history-feedback]").textContent,"Lançamento excluído.");
console.log("Integrated deletion: cancellation, focus, failure/retry, duplicate prevention and preserved category passed.");
