import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const html = fs.readFileSync("src/income_analytics/api/static/index.html", "utf8");
assert.match(html, /<details id="understand-period" class="period-disclosure">/);
assert.match(html, /<span class="period-disclosure-action">Alterar período<\/span>/);
assert.match(html, /<form id="wealth-explanation-form" class="period-form">/);
assert.doesNotMatch(html, /<section class="card understand-period">/);
const styles = fs.readFileSync("src/income_analytics/api/static/css/app.css", "utf8");
assert.match(styles, /\.period-form input \{ width:148px; min-height:36px;/);
assert.match(styles, /\.period-form button \{ min-height:34px;/);

const source = fs
  .readFileSync("src/income_analytics/api/static/js/shared/dates.js", "utf8")
  .replace(/export /g, "");

function loadDates(start = "", end = "") {
  const inputs = {
    "#wealth-start-date": { value: start },
    "#wealth-end-date": { value: end },
  };
  const context = {
    URLSearchParams,
    window: { location: { search: "" } },
    document: { querySelector: selector => inputs[selector] ?? null },
  };
  vm.createContext(context);
  vm.runInContext(`${source}\nthis.api = { previousCalendarMonth, setUnderstandDefaultPeriod };`, context);
  return { ...context.api, inputs };
}

const cases = [
  [new Date(2026, 8, 24, 12), "2026-08-01", "2026-08-31"],
  [new Date(2026, 8, 1, 12), "2026-08-01", "2026-08-31"],
  [new Date(2027, 0, 5, 12), "2026-12-01", "2026-12-31"],
  [new Date(2027, 2, 1, 12), "2027-02-01", "2027-02-28"],
  [new Date(2028, 2, 1, 12), "2028-02-01", "2028-02-29"],
];

for (const [today, expectedStart, expectedEnd] of cases) {
  const { previousCalendarMonth } = loadDates();
  assert.deepEqual(
    { ...previousCalendarMonth(today) },
    { start: expectedStart, end: expectedEnd },
  );
}

{
  const { setUnderstandDefaultPeriod, inputs } = loadDates();
  setUnderstandDefaultPeriod(
    new Date(2026, 8, 24, 12),
    "?start_date=2026-04-10&end_date=2026-05-20",
  );
  assert.equal(inputs["#wealth-start-date"].value, "2026-04-10");
  assert.equal(inputs["#wealth-end-date"].value, "2026-05-20");
}

{
  const { setUnderstandDefaultPeriod, inputs } = loadDates("2026-07-03", "2026-07-17");
  setUnderstandDefaultPeriod(new Date(2026, 8, 24, 12), "");
  assert.equal(inputs["#wealth-start-date"].value, "2026-07-03");
  assert.equal(inputs["#wealth-end-date"].value, "2026-07-17");
}

console.log("Entender default period tests passed.");
