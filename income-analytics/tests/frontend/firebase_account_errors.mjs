import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync("src/income_analytics/api/static/js/account.js", "utf8");
const start = source.indexOf("function readableError(error) {");
const end = source.indexOf("async function action(callback)", start);
const context = vm.createContext({});
vm.runInContext(source.slice(start, end), context);
for (const [code, expected] of [
  ["auth/internal-error", "contate o suporte"],
  ["auth/unauthorized-domain", "endereço ainda não está autorizado"],
  ["auth/popup-blocked", "bloqueou a janela"],
  ["auth/network-request-failed", "conexão"],
  ["auth/operation-not-allowed", "método de acesso"],
  ["auth/invalid-credential", "recupere sua senha"],
]) {
  const message = context.readableError({code, message: "PRIVATE PROVIDER DETAIL"});
  assert.ok(message.includes(expected), code);
  assert.ok(!message.includes("PRIVATE"));
}
console.log("Firebase errors: provider, browser and credential failures have distinct safe messages.");
