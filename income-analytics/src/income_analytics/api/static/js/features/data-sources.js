import { portfolioApi } from "../api.js";
import { errorState, loadingState } from "../shared/ui.js";

export async function renderDataSources() {
  const target = document.querySelector("#fx-card");
  if (!target) return;
  if (!document.querySelector("#data-sources-card")) (document.querySelector("#paid-income-settings") || target).insertAdjacentHTML("afterend", '<section class="card" id="data-sources-card"><h2>Fontes de dados</h2><div id="data-sources">Carregando…</div></section>');
  const output = document.querySelector("#data-sources");
  output.innerHTML = loadingState;
  try {
    const data = await portfolioApi.dataSources();
    output.replaceChildren();
    const providers = (data.providers || []).filter(item => item.group !== "Agendamentos do sistema");
    if (!providers.length) {
      output.textContent = "As fontes de dados estão indisponíveis no momento.";
      return;
    }
    const grid = document.createElement("div");
    grid.className = "settings-provider-grid";
    const labels = {
      OK: "Última consulta concluída",
      UNKNOWN: "Consulta sob demanda",
      DEGRADED: "Consulta instável",
    };
    providers.forEach(item => {
      const card = document.createElement("article");
      card.className = "settings-provider";
      const name = document.createElement("h3");
      name.textContent = item.provider;
      const description = document.createElement("p");
      description.textContent = item.description;
      const status = document.createElement("small");
      status.textContent = labels[item.status] || "Temporariamente indisponível";
      card.append(name, description, status);
      grid.append(card);
    });
    output.append(grid);
    const note = document.createElement("p");
    note.className = "field-help";
    note.textContent = "A cobertura varia por ativo. Esta lista não indica sincronização bancária automática nem garante atualização em tempo real.";
    output.append(note);
  } catch (error) { output.innerHTML = errorState(error); }
}
