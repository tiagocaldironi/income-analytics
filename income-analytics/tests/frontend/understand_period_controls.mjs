import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const html = fs.readFileSync("src/income_analytics/api/static/index.html", "utf8");
const ids = ["wealth-explanation-form", "understand-period", "understand-period-validation",
  "wealth-start-date", "wealth-end-date", "apply-understand-period",
  "cancel-understand-period", "understand-period-value", "understand-period-status",
  "understand-questions"];
const elements = new Map();
function element() {
  return {
    value: "", hidden: true, disabled: false, open: false, textContent: "", events: {},
    classList: { add() {}, remove() {} },
    addEventListener(type, handler) { this.events[type] = handler; },
    setAttribute() {}, removeAttribute() {}, focus() {},
    querySelector() { return trigger; },
  };
}
const trigger = element();
for (const id of ids) {
  assert.ok(html.includes(`id="${id}"`), `actual markup must provide ${id}`);
  elements.set(`#${id}`, element());
}
const get = id => elements.get(`#${id}`);
const document = {
  events: {}, querySelector: selector => elements.get(selector) ?? null,
  addEventListener(type, handler) { this.events[type] = handler; },
};
let request;
let calls = 0;
const context = vm.createContext({
  document, window: { requestAnimationFrame: callback => callback() },
  performance: { now: () => 0, measure() {} },
  portfolioApi: { wealthExplanation: (...args) => { calls++; return request(...args); } },
});
let source = fs.readFileSync("src/income_analytics/api/static/js/features/performance.js", "utf8")
  .replace(/^import .*;\r?\n/gm, "").replaceAll("export ", "");
// Isolate period controls from the financial answer renderer.
source += "\nrenderExplanation = data => { contributionData = data; };";
vm.runInContext(source, context);
const initial = { start_date: "2026-09-01", end_date: "2026-09-30" };
get("wealth-start-date").value = initial.start_date;
get("wealth-end-date").value = initial.end_date;
context.bindPerformance();
request = async () => ({ period: initial });
await context.loadExplanation();
const appliedLabel = get("understand-period-value").textContent;
const panel = get("understand-period");
const open = () => { panel.open = true; panel.events.toggle(); };
open();
get("wealth-start-date").value = "2026-08-01";
get("cancel-understand-period").events.click();
assert.equal(get("wealth-start-date").value, initial.start_date);
assert.equal(panel.open, false);
open();
get("wealth-end-date").value = "2026-10-01";
document.events.keydown({ key: "Escape", preventDefault() {} });
assert.equal(get("wealth-end-date").value, initial.end_date);
assert.equal(panel.open, false);
open();
get("wealth-start-date").value = "2026-10-01";
get("wealth-explanation-form").events.submit({ preventDefault() {} });
assert.equal(calls, 1, "inverted dates must not reach the API");
assert.equal(get("understand-period-validation").hidden, false);
get("wealth-start-date").value = "2026-08-01";
let reject;
request = () => new Promise((_, rejectRequest) => { reject = rejectRequest; });
const pending = context.loadExplanation();
assert.equal(get("apply-understand-period").disabled, true);
assert.equal(get("understand-period-value").textContent, appliedLabel);
reject(new Error("offline"));
await pending;
assert.equal(get("wealth-start-date").value, initial.start_date);
assert.equal(get("understand-period-value").textContent, appliedLabel);
assert.equal(get("understand-period-status").hidden, false);
assert.equal(get("apply-understand-period").disabled, false);
request = async () => ({ period: { start_date: "2026-08-01", end_date: "2026-08-31" } });
await context.loadExplanation();
assert.match(get("understand-period-value").textContent, /01\/08\/2026/);
assert.equal(panel.open, false);
assert.equal(get("understand-period-status").hidden, true);
console.log("Period controls: markup, cancel, Escape, invalid dates, pending/failure and success passed.");
