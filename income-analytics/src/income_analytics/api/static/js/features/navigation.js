const defaultPage = "minha-carteira";
let navigationBound = false;

function pageFromHash() {
  const page = window.location.hash.slice(1).split("/")[0];
  return document.querySelector(`[data-page="${page}"]`) ? page : defaultPage;
}

export function showCurrentPage() {
  const page = pageFromHash();
  document.querySelectorAll("[data-page]").forEach(section => {
    section.hidden = section.dataset.page !== page;
  });
  document.querySelectorAll("[data-navigate]").forEach(link => {
    link.setAttribute("aria-current", link.getAttribute("href") === `#${page}` ? "page" : "false");
  });
  document.querySelector("#navigation-status").textContent = `Área ${page.replace("-", " ")} aberta.`;
  document.dispatchEvent(new CustomEvent("income:routechange", { detail: { route: page } }));
  if (page === "ajuda-metodologia") {
    const concept = window.location.hash.slice(1).split("/")[1];
    if (concept) requestAnimationFrame(() => document.getElementById(concept)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }
  return page;
}

export function bindNavigation() {
  if (navigationBound) return;
  navigationBound = true;
  window.addEventListener("hashchange", showCurrentPage);
  if (!window.location.hash) history.replaceState(null, "", `#${defaultPage}`);
  showCurrentPage();
}
