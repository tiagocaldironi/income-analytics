import { portfolioApi } from "../api.js";
import { applyPortfolioTheme } from "./wallet-settings.js";

const STORAGE_KEY = "income.activePortfolioId";
let portfolios = [];
let lifecycle = null;
let switchSequence = 0;

function activePortfolio() {
  return portfolios.find(item => item.id === localStorage.getItem(STORAGE_KEY)) || null;
}

function renderSelector() {
  const options = document.querySelector("#portfolio-options");
  if (!options) return;
  const current = localStorage.getItem(STORAGE_KEY);
  options.replaceChildren(...portfolios.map(item => {
    const option = document.createElement("button");
    option.type = "button";
    option.className = "portfolio-option";
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", String(item.id === current));
    const name = document.createElement("span");
    name.className = "portfolio-option-name";
    name.textContent = item.name;
    option.append(name);
    if (item.status !== "ACTIVE") {
      const archived = document.createElement("small");
      archived.textContent = "Arquivada";
      option.append(archived);
    } else if (item.id === current) {
      const active = document.createElement("span");
      active.className = "portfolio-option-check";
      active.setAttribute("aria-hidden", "true");
      active.textContent = "✓";
      option.append(active);
    }
    option.addEventListener("click", async () => {
      if (item.status === "ACTIVE") {
        document.querySelector("#portfolio-menu")?.removeAttribute("open");
        await activate(item.id);
      } else {
        localStorage.setItem(STORAGE_KEY, item.id);
        renderSelector();
      }
    });
    return option;
  }));
  const selected = activePortfolio();
  applyPortfolioTheme(selected?.id);
  const currentName = document.querySelector("#portfolio-current-name");
  if (currentName) currentName.textContent = selected?.name || "Carteira";
  const homeName = document.querySelector("#home-wallet-name");
  if (homeName) homeName.textContent = selected?.name || "Sua carteira";
  const archive = document.querySelector("#portfolio-archive");
  const restore = document.querySelector("#portfolio-restore");
  if (archive) archive.disabled = !selected || selected.status !== "ACTIVE";
  if (restore) restore.disabled = !selected || selected.status === "ACTIVE";
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
  applyPortfolioTheme(id);
  renderSelector();
  if (lifecycle && sequence === switchSequence) {
    const route = location.hash.replace(/^#/, "").split("/")[0] || "minha-carteira";
    await lifecycle.activate(route);
  }
}

export async function setupPortfolioContext(routeLifecycle) {
  lifecycle = routeLifecycle;
  const closeMenu = () => document.querySelector("#portfolio-menu")?.removeAttribute("open");
  document.querySelector("#portfolio-menu-trigger")?.addEventListener("click", event => {
    event.preventDefault();
    const menu = document.querySelector("#portfolio-menu");
    menu?.toggleAttribute("open");
  });
  document.addEventListener("click", event => {
    const menu = document.querySelector("#portfolio-menu");
    if (menu?.open && !menu.contains(event.target)) menu.removeAttribute("open");
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") closeMenu();
  });
  document.querySelector("#portfolio-create")?.addEventListener("click", async () => {
    closeMenu();
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
  window.addEventListener("income:portfolio-renamed", () => reloadPortfolios());
  document.querySelector("#portfolio-archive")?.addEventListener("click", async () => {
    closeMenu();
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
    closeMenu();
    const current = activePortfolio();
    if (!current) return;
    try {
      await portfolioApi.restorePortfolio(current.id);
      await reloadPortfolios();
      const route = location.hash.replace(/^#/, "").split("/")[0] || "minha-carteira";
      await lifecycle?.activate(route);
    } catch (error) {
      window.alert(error.message);
    }
  });
  await reloadPortfolios();
  return activePortfolio();
}
