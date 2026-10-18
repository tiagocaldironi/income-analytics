import { portfolioApi } from "../api.js";

const ACTIVE_PORTFOLIO_KEY = "income.activePortfolioId";
const THEMES_KEY = "income.portfolioThemes.v1";
const THEMES = new Set(["light", "dark"]);

function savedThemes() {
  try {
    const parsed = JSON.parse(localStorage.getItem(THEMES_KEY) || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

export function applyPortfolioTheme(portfolioId = localStorage.getItem(ACTIVE_PORTFOLIO_KEY)) {
  if (typeof document === "undefined" || !document.documentElement) return;
  const theme = savedThemes()[portfolioId] || "dark";
  document.documentElement.dataset.theme = THEMES.has(theme) ? theme : "dark";
}

function renderThemeSelection(theme) {
  document.querySelectorAll("[data-wallet-theme]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.walletTheme === theme));
  });
}

export async function loadWalletSettings() {
  const id = localStorage.getItem(ACTIVE_PORTFOLIO_KEY);
  const message = document.querySelector("#wallet-name-message");
  const nameInput = document.querySelector("#wallet-name");
  const heading = document.querySelector("#wallet-settings-name");
  if (!id || !nameInput) return;
  try {
    const result = await portfolioApi.listPortfolios();
    const selected = (result.portfolios || []).find(item => item.id === id && item.status === "ACTIVE");
    if (!selected) {
      if (message) message.textContent = "Selecione uma carteira ativa para editar suas configurações.";
      return;
    }
    nameInput.value = selected.name;
    if (heading) heading.textContent = selected.name;
    if (message) message.textContent = "";
    renderThemeSelection(savedThemes()[id] || "dark");
  } catch (error) {
    if (message) message.textContent = error.message || "Não foi possível carregar as configurações da carteira.";
  }
}

export function setupWalletSettings() {
  const form = document.querySelector("#wallet-name-form");
  form?.addEventListener("submit", async event => {
    event.preventDefault();
    const id = localStorage.getItem(ACTIVE_PORTFOLIO_KEY);
    const input = document.querySelector("#wallet-name");
    const message = document.querySelector("#wallet-name-message");
    const name = input?.value.trim() || "";
    if (!id || !name || name.length > 100) {
      if (message) message.textContent = "Informe um nome com até 100 caracteres.";
      return;
    }
    try {
      const renamed = await portfolioApi.renamePortfolio(id, name);
      if (input) input.value = renamed.name;
      const heading = document.querySelector("#wallet-settings-name");
      if (heading) heading.textContent = renamed.name;
      const currentName = document.querySelector("#portfolio-current-name");
      if (currentName) currentName.textContent = renamed.name;
      if (message) message.textContent = "Nome da carteira atualizado.";
      window.dispatchEvent(new Event("income:portfolio-renamed"));
    } catch (error) {
      if (message) message.textContent = error.message || "Não foi possível atualizar o nome da carteira.";
    }
  });

  document.querySelectorAll("[data-wallet-theme]").forEach(button => {
    button.addEventListener("click", () => {
      const id = localStorage.getItem(ACTIVE_PORTFOLIO_KEY);
      const theme = button.dataset.walletTheme;
      if (!id || !THEMES.has(theme)) return;
      try {
        const themes = savedThemes();
        themes[id] = theme;
        localStorage.setItem(THEMES_KEY, JSON.stringify(themes));
        applyPortfolioTheme(id);
        renderThemeSelection(theme);
      } catch {
        const message = document.querySelector("#wallet-theme-message");
        if (message) message.textContent = "Não foi possível salvar o tema neste navegador.";
      }
    });
  });
}
