import { portfolioApi } from "../api.js";
import { errorState, loadingState, table } from "../shared/ui.js";

export async function renderDataSources() {
  const target = document.querySelector("#fx-card");
  if (!target) return;
  if (!document.querySelector("#data-sources-card")) target.insertAdjacentHTML("afterend", '<section class="card" id="data-sources-card"><h2>Fontes de dados</h2><div id="data-sources">Carregando…</div></section>');
  const output = document.querySelector("#data-sources");
  output.innerHTML = loadingState;
  try {
    const data = await portfolioApi.dataSources();
    const renderGroup = (title, providers) => providers.length ? `<h3>${title}</h3>${table(["Fonte", "Processo", "Status", "Próxima execução", "Último sucesso"], providers.map(item => `<tr><td>${item.provider}</td><td>${item.description}</td><td data-tone="${item.status === "OK" ? "positive" : item.status === "UNKNOWN" ? "" : "negative"}">${item.status === "OK" ? "Atualizada" : item.status === "UNKNOWN" ? "Sem atualização" : item.status === "DEGRADED" ? "Instável" : "Indisponível"}</td><td>${item.next_execution ? new Date(item.next_execution).toLocaleString("pt-BR") : item.execution_note || "—"}</td><td>${item.last_success ? new Date(item.last_success).toLocaleString("pt-BR") : "—"}</td></tr>`))}` : "";
    output.innerHTML = renderGroup("Fontes de dados", data.providers.filter(item => item.group !== "Agendamentos do sistema")) + renderGroup("Agendamentos do sistema", data.providers.filter(item => item.group === "Agendamentos do sistema"));
  } catch (error) { output.innerHTML = errorState(error); }
}
