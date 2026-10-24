import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
class Node {
  constructor(tag) { this.tag = tag; this.children = []; this.textContent = ""; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren() { this.children = []; this.innerHTML = ""; }
}
const output = new Node("div");
const malicious = '<img src=x onerror="alert(1)">';
let providers = [
  {provider: malicious, description: malicious, status: "UNKNOWN"},
  {provider: "Scheduler", description: "private", group: "Agendamentos do sistema"},
];
const context = vm.createContext({
  document: {querySelector: selector => selector === "#data-sources" ? output : new Node("section"), createElement: tag => new Node(tag)},
  portfolioApi: {dataSources: async () => ({providers})},
  loadingState: "Loading", errorState: () => "Error",
});
vm.runInContext(fs.readFileSync("src/income_analytics/api/static/js/features/data-sources.js", "utf8")
  .replace(/^import .*;$/gm, "").replace("export async function", "async function"), context);
await context.renderDataSources();
assert.equal(output.children[0].children.length, 1, "internal schedules stay out of the catalog");
const card = output.children[0].children[0];
assert.equal(card.children[0].textContent, malicious);
assert.equal(card.children[1].textContent, malicious);
assert.equal(card.children[0].children.length, 0, "untrusted names remain text");
assert.equal(card.children[2].textContent, "Consulta sob demanda");
providers = [];
await context.renderDataSources();
assert.equal(output.children.length, 0, "stale cards are removed");
assert.match(output.textContent, /indisponíveis/);
console.log("Settings sources: safe DOM, schedule exclusion and empty state passed.");
