import { portfolioApi } from "../api.js";
import { friendlyError, setMessage, validateForm, withProcessing } from "../shared/ui.js";
let benchmarkBound = false;

export function bindBenchmark() {
  if (benchmarkBound) return;
  const form = document.querySelector("#cdi-form");
  if (!form) return;
  benchmarkBound = true;
  form?.insertAdjacentHTML("beforeend", '<button type="button" class="secondary" id="refresh-cdi">Atualizar CDI automaticamente</button><div id="refresh-cdi-message" class="message" role="alert"></div>');
  document.querySelector("#refresh-cdi")?.addEventListener("click", async event => {
    const message = document.querySelector("#refresh-cdi-message");
    const end = new Date().toLocaleDateString("en-CA");
    const start = new Date(Date.now() - 31 * 86400000).toLocaleDateString("en-CA");
    try {
      const result = await withProcessing(event.currentTarget, () => portfolioApi.refreshBenchmark("CDI", start, end), "Atualizando…");
      setMessage(message, `${result.observations} observações de CDI atualizadas automaticamente.`);
    } catch (error) { setMessage(message, friendlyError(error), "error"); }
  });
  form?.insertAdjacentHTML("beforeend", '<button type="button" class="secondary" id="refresh-benchmarks">Atualizar CDI, IPCA e IBOV</button><div id="refresh-benchmarks-message" class="message" role="alert"></div>');
  document.querySelector("#refresh-benchmarks")?.addEventListener("click", async event => {
    const message = document.querySelector("#refresh-benchmarks-message");
    const end = new Date().toLocaleDateString("en-CA");
    const start = new Date(Date.now() - 31 * 86400000).toLocaleDateString("en-CA");
    try {
      const results = await withProcessing(event.currentTarget, () => Promise.all(["CDI", "IPCA", "IBOV"].map(name => portfolioApi.refreshBenchmark(name, start, end))), "Atualizando…");
      setMessage(message, `Benchmarks atualizados: ${results.map(item => item.benchmark).join(", ")}.`);
    } catch (error) { setMessage(message, friendlyError(error), "error"); }
  });
  document.querySelector("#cdi-form")?.addEventListener("submit", async event => {
    event.preventDefault();
    if (!validateForm(event.currentTarget)) return;
    const message = document.querySelector("#cdi-message");
    try {
      await withProcessing(event.currentTarget.querySelector("button[type=submit]"), () => portfolioApi.benchmark("CDI", {
        return_percentage: Number(document.querySelector("#cdi-return").value) / 100,
        effective_date: document.querySelector("#cdi-date").value,
      }));
      setMessage(message, "CDI registrado.");
    } catch (error) { setMessage(message, friendlyError(error), "error"); }
  });
}
