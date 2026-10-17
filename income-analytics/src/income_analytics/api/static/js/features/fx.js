import { portfolioApi } from "../api.js";
import { friendlyError, setMessage, withProcessing } from "../shared/ui.js";
let fxBound = false;

export function bindFx() {
  if (fxBound) return;
  const target = document.querySelector(".danger-zone");
  if (!target) return;
  fxBound = true;
  target.insertAdjacentHTML("beforebegin", '<section class="card" id="fx-card"><h2>Moeda-base e câmbio</h2><p>O patrimônio é consolidado em BRL. Para ativos em USD, atualize a PTAX da data desejada.</p><button type="button" class="secondary" id="refresh-usd-brl">Atualizar USD/BRL</button><div class="message" id="fx-message" role="alert"></div></section>');
  document.querySelector("#refresh-usd-brl")?.addEventListener("click", async event => {
    const message = document.querySelector("#fx-message");
    const date = new Date().toLocaleDateString("en-CA");
    try {
      const result = await withProcessing(event.currentTarget, () => portfolioApi.refreshFx("USD", "BRL", date), "Atualizando…");
      setMessage(message, `USD/BRL atualizado: 1 USD = R$ ${Number(result.rate).toFixed(4)}.`);
      window.portfolioLoad?.();
    } catch (error) { setMessage(message, friendlyError(error), "error"); }
  });
}
