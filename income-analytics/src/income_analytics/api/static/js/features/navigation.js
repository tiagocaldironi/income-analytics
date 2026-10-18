const defaultPage = "minha-carteira";
let navigationBound = false;
let lastDispatchedPage = null;

function pageFromHash() {
  const page = window.location.hash.slice(1).split("/")[0];
  return document.querySelector(`[data-page="${page}"]`) ? page : defaultPage;
}

export function showCurrentPage() {
  const page = pageFromHash();
  const nestedRoute = window.location.hash.slice(1).split("/")[1];
  const mobileShell = window.matchMedia("(max-width: 767px), (max-height: 480px) and (orientation: landscape)").matches;
  document.querySelectorAll("[data-page]").forEach(section => {
    section.hidden = section.dataset.page !== page;
  });
  document.querySelectorAll("[data-navigate]").forEach(link => {
    link.setAttribute("aria-current", link.getAttribute("href") === `#${page}` ? "page" : "false");
  });
  const mobileRoute = nestedRoute === "ativos" ? "portfolio" : page === "minha-carteira" ? "home" : page === "entender" ? "understand" : page.startsWith("tools-magic-formula") ? "act" : "";
  document.querySelectorAll("[data-mobile-nav]").forEach(link => {
    if (link.dataset.mobileNav === mobileRoute) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  const pageTitle = document.querySelector(`[data-page="${page}"] h1`)?.textContent?.trim();
  const workspaceName = document.querySelector(".workspace-name");
  if (workspaceName) workspaceName.textContent = pageTitle || "Minha carteira";
  document.querySelector("#navigation-status").textContent = `Área ${page.replace("-", " ")} aberta.`;
  document.querySelector("#mobile-more-menu")?.close();
  if (page !== lastDispatchedPage) {
    lastDispatchedPage = page;
    document.dispatchEvent(new CustomEvent("income:routechange", { detail: { route: page } }));
  }
  if (page === "ajuda-metodologia") {
    const concept = window.location.hash.slice(1).split("/")[1];
    if (concept) requestAnimationFrame(() => document.getElementById(concept)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }
  if (mobileShell && page === "minha-carteira" && nestedRoute === "ativos") {
    window.setTimeout(() => document.querySelector("#positions")?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
  } else if (mobileShell && (page !== "minha-carteira" || !nestedRoute)) {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  return page;
}

export function bindNavigation() {
  if (navigationBound) return;
  navigationBound = true;
  window.addEventListener("hashchange", showCurrentPage);
  document.querySelector("[data-mobile-more]")?.addEventListener("click", () => document.querySelector("#mobile-more-menu")?.showModal());
  document.querySelector("[data-close-mobile-more]")?.addEventListener("click", () => document.querySelector("#mobile-more-menu")?.close());
  document.querySelector("#mobile-more-menu")?.addEventListener("click", event => {
    if (event.target === event.currentTarget) event.currentTarget.close();
  });
  if (!window.location.hash) history.replaceState(null, "", `#${defaultPage}`);
  showCurrentPage();
}
