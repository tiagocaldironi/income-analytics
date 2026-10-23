import assert from "node:assert/strict";
import fs from "node:fs";

const css = fs.readFileSync("src/income_analytics/api/static/css/account.css", "utf8");
const roots = [...css.matchAll(/:root(?:\[data-theme=light\])?\{([^}]+)\}/g)];
assert.equal(roots.length, 2);
function luminance(hex) {
  const rgb = hex.slice(1).match(/../g).map(value => parseInt(value, 16) / 255)
    .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
  return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
}
function contrast(a, b) {
  const [light, dark] = [luminance(a), luminance(b)].sort((a, b) => b - a);
  return (light + .05) / (dark + .05);
}
for (const [, declarations] of roots) {
  const tokens = Object.fromEntries([...declarations.matchAll(/--([\w-]+):(#[\da-f]{6})/gi)]
    .map(([, key, value]) => [key, value]));
  for (const background of ["bg", "surface"]) {
    for (const text of ["text", "muted", "accent", "error"])
      assert.ok(contrast(tokens[text], tokens[background]) >= 4.5, `${text}/${background} text must pass AA`);
    for (const control of ["control-line", "focus"])
      assert.ok(contrast(tokens[control], tokens[background]) >= 3, `${control}/${background} control must pass AA`);
  }
  assert.ok(contrast(tokens["on-accent"], tokens.accent) >= 4.5);
}
console.log("Account contrast: text, links, controls and focus pass AA in both themes.");
