import { mountAccountMenu } from "./account-menu.js";
import { authRequest, clearPrivateBrowserState } from "./auth-client.js";

async function start() {
  const config = await authRequest("/config");
  if (config.mode === "firebase") {
    let account;
    try { account = await authRequest("/me"); }
    catch { location.replace("/entrar"); return; }
    const previous = localStorage.getItem("income.authUser");
    if (previous !== account.user_id) localStorage.removeItem("income.activePortfolioId");
    sessionStorage.setItem("income.userId", account.user_id);
    localStorage.setItem("income.authUser", account.user_id);
    const response = await fetch("/api/portfolios", { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) { location.replace("/entrar"); return; }
    const { portfolios } = await response.json();
    if (!portfolios.some(wallet => wallet.status === "ACTIVE")) { location.replace("/primeiro-acesso"); return; }
    const current = localStorage.getItem("income.activePortfolioId");
    if (!portfolios.some(wallet => wallet.id === current && wallet.status === "ACTIVE"))
      localStorage.setItem("income.activePortfolioId", portfolios.find(wallet => wallet.status === "ACTIVE").id);
    const leave = () => {
      document.body.replaceChildren();
      location.replace("/entrar");
    };
    window.addEventListener("storage", event => {
      if (event.key === "income.authUser" && event.newValue !== account.user_id) leave();
    });
    if (typeof BroadcastChannel !== "undefined") {
      const channel = new BroadcastChannel("income-auth");
      channel.addEventListener("message", leave);
    }
    window.addEventListener("pageshow", event => { if (event.persisted) location.reload(); });
    mountAccountMenu(document.querySelector(".brand-row"));
    // Financial data never remains displayed after a backend session rejection.
    window.addEventListener("income:session-expired", () => {
      clearPrivateBrowserState(); leave();
    });
  }
  document.documentElement.classList.remove("auth-pending");
  await import("./app.js");
}
start().catch(() => {
  document.documentElement.classList.remove("auth-pending");
  const text = document.createElement("p");
  text.textContent = "Não foi possível iniciar o Income. Atualize a página para tentar novamente.";
  document.body.replaceChildren(text);
});
