import { portfolioApi } from "../api.js";

const STORAGE_KEY = "income.activePortfolioId";
let portfolios = [];
let lifecycle = null;
let switchSequence = 0;

function activePortfolio() {
  return portfolios.find(item => item.id === localStorage.getItem(STORAGE_KEY)) || null;
}

function renderSelector() {
  const selector = document.querySelector("#portfolio-selector");
  if (!selector) return;
  const current = localStorage.getItem(STORAGE_KEY);
  selector.replaceChildren(...portfolios.map(item => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.status === "ACTIVE" ? item.name : `${item.name} (arquivada)`;
    option.selected = item.id === current;
    return option;
  }));
  const selected = activePortfolio();
  const workspaceName = document.querySelector(".workspace-name");
  if (workspaceName) workspaceName.textContent = selected?.name || "";
  document.querySelector("#portfolio-archive").disabled = !selected || selected.status !== "ACTIVE";
  document.querySelector("#portfolio-rename").disabled = !selected || selected.status !== "ACTIVE";
  document.querySelector("#portfolio-restore").disabled = !selected || selected.status === "ACTIVE";
}

async function reloadPortfolios({ selectFallback = false } = {}) {
  const result = await portfolioApi.listPortfolios();
  portfolios = result.portfolios || [];
  const current = portfolios.find(item => item.id === localStorage.getItem(STORAGE_KEY));
  if (!current || (selectFallback && current.status !== "ACTIVE")) {
    const main = portfolios.find(item => item.id === "7a54eeb7-542a-5832-8544-8be7dcb0237e" && item.status === "ACTIVE");
    const firstActive = portfolios.find(item => item.status === "ACTIVE");
    const fallback = main || firstActive || portfolios[0];
    if (fallback) localStorage.setItem(STORAGE_KEY, fallback.id);
  }
  renderSelector();
}

async function activate(id) {
  const sequence = ++switchSequence;
  localStorage.setItem(STORAGE_KEY, id);
  renderSelector();
  if (lifecycle && sequence === switchSequence) {
    const route = location.hash.replace(/^#/, "").split("/")[0] || "minha-carteira";
    await lifecycle.activate(route);
  }
}

export async function setupPortfolioContext(routeLifecycle) {
  lifecycle = routeLifecycle;
  const selector = document.querySelector("#portfolio-selector");
  selector?.addEventListener("change", event => activate(event.target.value));
  document.querySelector("#portfolio-create")?.addEventListener("click", async () => {
    const name = window.prompt("Nome da nova carteira:");
    if (name === null) return;
    try {
      const created = await portfolioApi.createPortfolio({ name, base_currency: "BRL" });
      await reloadPortfolios();
      await activate(created.id);
    } catch (error) {
      window.alert(error.message);
    }
  });
  document.querySelector("#portfolio-rename")?.addEventListener("click", async () => {
    const current = activePortfolio();
    if (!current) return;
    const name = window.prompt("Novo nome da carteira:", current.name);
    if (name === null) return;
    try {
      await portfolioApi.renamePortfolio(current.id, name);
      await reloadPortfolios();
    } catch (error) {
      window.alert(error.message);
    }
  });
  document.querySelector("#portfolio-archive")?.addEventListener("click", async () => {
    const current = activePortfolio();
    if (!current || !window.confirm(`Arquivar “${current.name}”? Os dados serão preservados.`)) return;
    try {
      await portfolioApi.archivePortfolio(current.id);
      await reloadPortfolios({ selectFallback: true });
      const selected = activePortfolio();
      if (selected) await activate(selected.id);
    } catch (error) {
      window.alert(error.message);
    }
  });
  document.querySelector("#portfolio-restore")?.addEventListener("click", async () => {
    const current = activePortfolio();
    if (!current) return;
    try {
      await portfolioApi.restorePortfolio(current.id);
      await reloadPortfolios();
    } catch (error) {
      window.alert(error.message);
    }
  });
  await reloadPortfolios();
  return activePortfolio();
}
