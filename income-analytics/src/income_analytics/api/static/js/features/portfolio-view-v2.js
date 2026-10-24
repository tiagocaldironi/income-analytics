import { renderPortfolioInsight } from "./portfolio-insights-v2.js";
import { renderPortfolioGuidance } from "./portfolio-guidance-v2.js";
import { icon } from "../shared/icons.js";
let bound = false;
let resizeCharts = () => {};
export function selectAnalysis(index, focus = false, interacted = false) {
  const tabs = [...document.querySelectorAll("[data-analysis-tab]")];
  const panels = [...document.querySelectorAll("[data-analysis-panel]")];
  if (!tabs.length) return;
  index = (index + tabs.length) % tabs.length;
  tabs.forEach((tab, i) => {
    tab.setAttribute("aria-selected", String(i === index));
    tab.tabIndex = i === index ? 0 : -1;
    panels[i].hidden = i !== index;
  });
  if (focus) tabs[index].focus();
  if (interacted) document.dispatchEvent(new CustomEvent("income:analysis-explored",{detail:{index}}));
  // Panels remain mounted: filters and loaded data survive every switch.
  requestAnimationFrame(() => resizeCharts());
}
export function setupSidebar() {
  const toggle = document.querySelector("#sidebar-toggle");
  if (toggle?.id !== "sidebar-toggle") return;
  const root = document.documentElement;
  const apply = collapsed => {
    root.classList.toggle("sidebar-collapsed", collapsed);
    toggle.setAttribute("aria-expanded", String(!collapsed));
    const label = collapsed ? "Expandir menu lateral" : "Recolher menu lateral";
    toggle.setAttribute("aria-label", label);
    toggle.title = label;
    requestAnimationFrame(() => resizeCharts());
  };
  // Only a display preference is stored; storage may be unavailable in private browsing.
  try { apply(localStorage.getItem("income.sidebar.collapsed") === "1"); } catch { apply(false); }
  toggle.addEventListener("click", () => {
    const collapsed = !root.classList.contains("sidebar-collapsed");
    apply(collapsed);
    try { localStorage.setItem("income.sidebar.collapsed", collapsed ? "1" : "0"); } catch {}
  });
}
export function setupPortfolioView(resize) {
  resizeCharts = resize;
  if (bound) return;
  bound = true;
  const region = document.querySelector("#portfolio-analysis");
  if (!region) return;
  region.addEventListener("click", event => {
    const tab = event.target.closest("[data-analysis-tab]");
    if (tab) selectAnalysis(Number(tab.dataset.analysisTab), false, true);
  });
  region.addEventListener("keydown", event => {
    const tab = event.target.closest("[data-analysis-tab]");
    if (!tab) return;
    const i = Number(tab.dataset.analysisTab);
    const next = {ArrowRight:i+1, ArrowLeft:i-1, Home:0, End:3}[event.key];
    if (next !== undefined) { event.preventDefault(); selectAnalysis(next, true, true); }
  });
  // Swipe is confined to navigation. Chart gestures/tooltips remain untouched.
  const strip = region.querySelector("[role=tablist]");
  let start = null;
  strip?.addEventListener("touchstart", event => {
    const t = event.changedTouches[0]; start = {x:t.clientX,y:t.clientY};
  }, {passive:true});
  strip?.addEventListener("touchend", event => {
    if (!start) return;
    const t = event.changedTouches[0], dx = t.clientX-start.x, dy = t.clientY-start.y;
    start = null;
    if (Math.abs(dx) < 65 || Math.abs(dx) < Math.abs(dy)*1.5) return;
    const current = Number(region.querySelector('[aria-selected="true"]').dataset.analysisTab);
    selectAnalysis(current+(dx<0?1:-1), false, true);
  }, {passive:true});
  const icons = ["wallet","chart","moneybag","layers"];
  document.querySelectorAll('[data-page="minha-carteira"] .metric').forEach((card,i) => {
    const node = document.createElement("span"); node.className = "metric-icon";
    node.innerHTML = icon(icons[i]); card.prepend(node);
    const help = document.createElement("details"); help.className = "metric-help";
    const label = card.querySelector("small")?.textContent || "indicador";
    const summary = document.createElement("summary"); summary.textContent = "i";
    summary.setAttribute("aria-label", `Como interpretar ${label}`);
    const copy = document.createElement("p");
    copy.textContent = ["Valor de mercado disponível na moeda-base da carteira. Valores incompletos permanecem identificados.","Retorno TWR dos últimos 12 meses. Depende da cobertura histórica e pode estar parcial ou indisponível.","Rendimentos registrados desde o início. Este total não representa rentabilidade percentual.","Custo de aquisição das posições atuais. É diferente do patrimônio de mercado e do capital líquido investido."][i];
    help.append(summary,copy); card.append(help);
  });
  document.querySelectorAll(".primary-nav a").forEach(link => {
    const route = link.getAttribute("href");
    const iconsByRoute = {"#minha-carteira":"wallet","#entender":"book","#estrategia":"compass","#simular":"chart","#operacoes":"income","#configuracoes":"settings","#ferramentas":"tools","#ajuda-metodologia":"help"};
    const label = document.createElement("span");
    label.className = "nav-label";
    label.textContent = link.textContent;
    link.setAttribute("aria-label", link.textContent.trim());
    link.textContent = "";
    link.insertAdjacentHTML("afterbegin",icon(iconsByRoute[route]));
    link.append(label);
  });
  setupSidebar();
  new MutationObserver(() => resizeCharts()).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
}
export function updatePortfolioView(dashboard) {
  const root = document.querySelector('[data-page="minha-carteira"]');
  if (!root) return;
  renderPortfolioGuidance(dashboard);
  renderPortfolioInsight(dashboard);
  root.dataset.hasPositions = String(dashboard.holdings.classes.some(group => group.assets.some(asset => !asset.target_only)));
}
